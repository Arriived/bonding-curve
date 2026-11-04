"""Matcher-authority signing.

Production signs in a KMS; the private key never enters this process:
  - gcp-kms: Google Cloud KMS, algorithm EC_SIGN_ED25519 ("EdDSA on the Curve25519 in pure mode (taking
    data as input)", google-cloud-kms 3.18.0 kms_v1/types/resources.py), REST
    `cryptoKeyVersions.asymmetricSign` with `data` (not `digest`) plus CRC32C integrity fields.
  - aws-kms: AWS KMS key spec ECC_NIST_EDWARDS25519, SigningAlgorithm ED25519_SHA_512 with
    MessageType RAW (pure Ed25519; messages 0-4096 bytes; botocore 1.43.124 kms/2014-11-01 model).
A Solana message is at most 1,232 bytes, inside both limits. Neither cloud integration has been run
against a real KMS from this repository; both are exercised against fakes in tests (see README).

Development only:
  - keyfile: a Solana keypair JSON file. Refused when MATCHER_ENV=production.

Every signature, whatever the backend, is verified against the expected public key before use, and
the service refuses to start unless that public key equals Config.matcher_authority on-chain.
"""
import base64
import json
import os

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature


class SignerUnavailable(Exception):
    pass


def _crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82F63B78 & -(crc & 1))
    return crc ^ 0xFFFFFFFF


def _spki_ed25519(der: bytes) -> bytes:
    # SubjectPublicKeyInfo for Ed25519 is a fixed 12-byte prefix (OID 1.3.101.112) + 32 key bytes.
    prefix = bytes.fromhex("302a300506032b6570032100")
    if len(der) != 44 or not der.startswith(prefix):
        raise SignerUnavailable("KMS public key is not an Ed25519 SubjectPublicKeyInfo")
    return der[12:]


class Signer:
    backend = "abstract"

    def __init__(self):
        self._pubkey = None

    @property
    def pubkey(self) -> Pubkey:
        if self._pubkey is None:
            self._pubkey = Pubkey.from_bytes(self._raw_pubkey())
        return self._pubkey

    def sign(self, message: bytes) -> bytes:
        try:
            sig = self._raw_sign(message)
        except SignerUnavailable:
            raise
        except Exception as e:  # any backend failure is "unavailable", never a partial result
            raise SignerUnavailable(f"{self.backend}: {type(e).__name__}: {e}") from e
        if len(sig) != 64 or not Signature.from_bytes(sig).verify(self.pubkey, message):
            raise SignerUnavailable(f"{self.backend}: returned signature does not verify against {self.pubkey}")
        return sig


class KeyfileSigner(Signer):
    backend = "keyfile"

    def __init__(self, path, env):
        super().__init__()
        if env == "production":
            raise SignerUnavailable("keyfile signer is refused when MATCHER_ENV=production; use a KMS backend")
        try:
            with open(path) as f:
                self._kp = Keypair.from_bytes(bytes(json.load(f)))
        except (OSError, ValueError) as e:
            raise SignerUnavailable(f"keyfile: cannot read {path}: {e}") from e

    def _raw_pubkey(self):
        return bytes(self._kp.pubkey())

    def _raw_sign(self, message):
        return bytes(self._kp.sign_message(message))


class GcpKmsSigner(Signer):
    """REST client for Cloud KMS. `key_version` is projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*."""
    backend = "gcp-kms"

    def __init__(self, key_version, http=None, token_provider=None):
        super().__init__()
        import httpx
        self.key_version = key_version
        self.http = http or httpx.Client(timeout=10.0)
        self.token_provider = token_provider or self._adc_token
        self.base = "https://cloudkms.googleapis.com/v1/"

    @staticmethod
    def _adc_token():
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloudkms"])
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token

    def _headers(self):
        return {"Authorization": f"Bearer {self.token_provider()}"}

    def _raw_pubkey(self):
        r = self.http.get(self.base + self.key_version + "/publicKey", headers=self._headers())
        r.raise_for_status()
        body = r.json()
        if body.get("algorithm") != "EC_SIGN_ED25519":
            raise SignerUnavailable(f"gcp-kms: key algorithm is {body.get('algorithm')}, need EC_SIGN_ED25519")
        pem = body["pem"]
        der = base64.b64decode("".join(l for l in pem.splitlines() if "-----" not in l))
        return _spki_ed25519(der)

    def _raw_sign(self, message):
        req = {"data": base64.b64encode(message).decode(), "dataCrc32c": str(_crc32c(message))}
        r = self.http.post(self.base + self.key_version + ":asymmetricSign", json=req, headers=self._headers())
        r.raise_for_status()
        body = r.json()
        if not body.get("verifiedDataCrc32c"):
            raise SignerUnavailable("gcp-kms: request data CRC32C was not verified by KMS")
        sig = base64.b64decode(body["signature"])
        if int(body.get("signatureCrc32c", -1)) != _crc32c(sig):
            raise SignerUnavailable("gcp-kms: response signature CRC32C mismatch")
        if body.get("name") != self.key_version:
            raise SignerUnavailable("gcp-kms: response key version differs from the configured one")
        return sig


class AwsKmsSigner(Signer):
    backend = "aws-kms"

    def __init__(self, key_id, client=None):
        super().__init__()
        self.key_id = key_id
        if client is None:
            import boto3
            client = boto3.client("kms")
        self.client = client

    def _raw_pubkey(self):
        r = self.client.get_public_key(KeyId=self.key_id)
        if r.get("KeySpec") != "ECC_NIST_EDWARDS25519":
            raise SignerUnavailable(f"aws-kms: key spec is {r.get('KeySpec')}, need ECC_NIST_EDWARDS25519")
        return _spki_ed25519(r["PublicKey"])

    def _raw_sign(self, message):
        r = self.client.sign(KeyId=self.key_id, Message=message, MessageType="RAW",
                             SigningAlgorithm="ED25519_SHA_512")
        return r["Signature"]


def from_config(cfg):
    if cfg.signer == "keyfile":
        return KeyfileSigner(cfg.keyfile, cfg.env)
    if cfg.signer == "gcp-kms":
        return GcpKmsSigner(cfg.gcp_key_version)
    if cfg.signer == "aws-kms":
        return AwsKmsSigner(cfg.aws_key_id)
    raise SignerUnavailable(f"unknown MATCHER_SIGNER {cfg.signer!r}")
