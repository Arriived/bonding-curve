## Paired devnet qualification status (12 November 2026)

The deployed paired program completed the five remaining authorized scenarios,
matching VM exactly (26 snapshots including the earlier completed case). Full
program smoke and negatives pass 34/34 from saved receipts. The host report
renderer then hit a Windows cp1252 encoding error. The owner-required halt
prevented the service stage: **no real matcher launch, door request or
independent live verdict was submitted**. Those checks remain outstanding.

Program commit `9594aad` fixes the report output with a regression that first
failed on `db8d718`. Service `310e12a` fixes the independent verifier's missing
NameLock replay for doors; two regressions first failed on `584596a`. All 180
service tests pass. The signed devnet client is prepared at `a7aa8c0`, and the
full 1,223-target evasion JSON remains byte-identical. No routing or
normalization rule changed. A passing offline suite is not live E2E evidence.

All test positions, entitled fees and operating-wallet balances were swept.
Closing treasury balance is 53.089376282 SOL at finalized slot 521,596,121.
Whole qualification cost is 3.454624079 SOL; this resume cost 0.255489721 SOL.
The reconciliation includes the earlier deployment and recovery and two later
5-SOL funding transfers. All 24 other wallets and all 50 token-owner scans
are empty. [Program measurements and every signature/slot](https://github.com/Arriived/bonding-curve/blob/claude/paired-doors/program/verification/devnet/paired-4437e58-resume/report.md).
