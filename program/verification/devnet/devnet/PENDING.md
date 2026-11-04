# Devnet end-to-end test: PENDING

The program is not deployed on devnet yet: the deploy wallet
`2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` has no devnet SOL
(docs/DEPLOYMENT.md, section 5). `devnet/e2e.sh` with `devnet/e2e-target` set
to `devnet` exits 3 with a PENDING message until then.

To complete it, from `program/` on the deploy source:

1. Fund the deploy wallet with about 3.5 devnet SOL.
2. `devnet/deploy.sh https://api.devnet.solana.com <keys_dir> verification/devnet/devnet`
3. Change the one line in `devnet/e2e-target` from `localnet` to `devnet`.
4. `devnet/e2e.sh <keys_dir>`

The outputs (deploy, Config read-back, smoke, failures, 33 checks) land in this
directory, and this file is deleted in the same commit.
