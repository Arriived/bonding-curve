# Working rules for this repository

Standing instructions from the owner. These outrank convenience.

## Secrets and keys

- **Never report a private key, in any form, anywhere.** Not in chat, not in a file, not in a log.
- For a keypair file, output only its path, its modified time and the derived **public** key. Never print, log or
  copy the contents.
- Keypairs are never committed. The matcher signing key is never in the repository and never in a plaintext
  environment variable in production.
- Devnet keypairs must never live in OneDrive or any synced folder. Mainnet keys belong in a hardware wallet or a
  KMS.

## Files and downloads

- **Download to this device. Never to OneDrive or any synced folder.**
- Temporary and intermediate files go in the session scratchpad, not the repository.

## Git

- **Always push work to GitHub.** Nothing of value stays only in a container; containers are reclaimed.
- Develop on the branch assigned for the task. Do not push to `main`.
- Do not open a pull request unless the owner asks for one.

## Terminology

- The paired-token design is called **paired doors**. Do not use the other project's name for it.

## Rejected approaches — do not reintroduce as routing

Symbol-only matching, fuzzy matching, image matching and social-link matching were each measured and rejected.
They may be used for flagging, never for routing. See `services/matcher/RULE_CANDIDATES.md` and
`services/matcher/CORRECTIONS.md`.

## Evidence

- A passing offline suite is not live end-to-end evidence. Say which it is.
- Report outcomes faithfully: if a test fails, show the output; if a step was skipped, say so.
- Numbers in documents carry the window and sample they came from.
