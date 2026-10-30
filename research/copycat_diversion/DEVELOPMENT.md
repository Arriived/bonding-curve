# Development record

- Reused the existing independent Decimal `Curve` and validated `FastBook`.
  The mathematical/rule design preceded the new implementation.
- The copy-buyer ownership clarification is implemented as the default. Treasury
  ownership, treasury exit, buy-and-lock and literal pricing-supply burn are
  distinct settings; they are never silently interchanged.
- Initial reference/routing/election tests passed. A full-suite collection error
  was a duplicate `test_attacks.py` module name; renaming the new test module
  resolved collection without changing the old tests.
- The first broad search stopped with a failed manifest. Repeated fully funded
  bundles could overdraw a float wallet by about 1e-12 because inverse square-root
  execution rounded up; accumulated burn-wallet dust could also trigger a later
  debit rejection. The failed output, source snapshot and original diagnostics
  are preserved in `development/failed_search_01/` and
  `original_boundary_failures.json`. They are excluded from findings.
- Quantities now round down to fit the existing engine's *actual* gross+fee
  expression; routed spending retains an eight-ulp funding margin, and transfer
  checks are strict. Unspent dust stays with its owner; balances are not clipped
  or secretly topped up. Sale gas affordability uses the actual net expression.
- All 416 targeted boundary scenarios passed after the fix. Three hostile-bundle
  fixtures and a direct repeated two-leg budget-depletion test are regression
  tests. The complete suite then passed **134 tests in 52.62 seconds**.
- Fixed elections stop tracking irrelevant post-latch scores as a performance
  optimization. This does not change a latched leader or funded execution.
- The 216-case controlled front-run search checks funded realized cash against
  the analytic prediction, with fees, network cost, minimum output and abstention.
  Cash self-transfers are excluded from external attacker receipts.
- The sequential production search was stopped after a complete, source-matched
  170-setting checkpoint to improve throughput. That checkpoint is preserved in
  `development/serial_training_prefix/`; completed candidate scores were reused,
  not counted as new observations. Ordinary local worker processes evaluated the
  remaining deterministic functions. A 12-row, two-setting/two-seed check matched
  serial seed records bit for bit (`development/parallel_parity.json`).
- The parallel wrapper preserves candidate order and selection, retains separate
  training/screen/confirmation seeds and deduplicates identical evaluation calls.
  Its manifest counts physical calls, with logical evaluation calls separate.
  Core model sources were unchanged during the execution.
- Broadened zero-tax spam/evasion controls to allow voluntary leader portfolios.
  The apparent default first/5% spam uplift against the narrow control vanished;
  it is not reported as evidence of a novel diversion exploit. Two regression
  tests verify that zero split matches the original control and outsider buys
  remain undiverted. The full **136-test suite passed in 46.02 seconds**.
- A restricted dashboard rerun hung before app execution in Windows' loopback
  socketpair initialization. The same full suite passed with local sockets
  available. The 134 non-dashboard tests also passed separately in 22.35 seconds.
- The badge audit found original fallback during undefined-leader periods.
  Independently retrained strict badge controls remove that favorable assumption;
  original raw results remain preserved. First-launch badges are unaffected.
  Two additional strict-badge regression tests passed in 4.68 seconds, bringing
  the verified project total to **138 distinct tests**, across the full suite
  and the added focused tests. No economic source was changed retroactively.

Only complete, source-matched production-study manifests are reported in
FINDINGS.md. Development smoke cases, interrupted runs and later independent
controls are labeled separately and never pooled into a fictitious seed count.

The user subsequently clarified that the winner may be any copy or the original.
`WINNER_REANALYSIS.md` corrects the overly original-focused interpretation and
reuses the completed 30-seed records to compare identity-free concentration.
The previous ranking/verdict is retained with an explicit scope correction.
No economic observations were changed or new simulations represented as run.
