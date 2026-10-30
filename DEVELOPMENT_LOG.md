# Development and verification log

## Environment and ordering

- Workspace began as an empty initialized Git repository.
- Bundled CPython 3.12.14 was available; Windows' `python` Store alias was not usable.
- A local virtual environment was prepared. Initial ensurepip failed because the
  sandbox temporary directory was not writable. Pointing TEMP/TMP at workspace
  `.tmp` resolved it. Network installation initially failed DNS in the sandbox;
  the permitted elevated package installation completed successfully.
- Phase 1 was implemented before dashboard construction. Its first executable
  run passed **21 tests in 5.44 seconds**, including deterministic Hypothesis
  properties for exact reserve differences and randomized valid sequences.
- Phase 2 tests passed **17 tests in 565.56 seconds**. That elapsed time overlapped
  dependency installation and slow first imports. It is not a trade benchmark.
- A subsequent 10,000-event, 10-token baseline benchmark completed in 0.6652
  seconds inside the Python process (seed 42; summary-only; local hardware).

## Design corrections during implementation

- Replaced per-trade tuple copies in the Decimal ledger with read-only balance
  views over private ledger storage to preserve O(1) accounting execution.
- Corrected wallet first-exit proceeds to use the full vector reserve difference,
  including cross terms between tokens held by the same wallet. Summed individual
  token quotes would overstate that wallet's executable liquidation value.
- Genesis positions are explicitly paid for by holder capital contributions.
  Trading cash is separate; reserve excess is a recorded donation buffer.
- The fast engine reports raw float discrepancy separately from a material
  shortfall after explicit tolerance. The Decimal ledger uses exact equality.
- Cross-token follower policies are labeled as synthetic followers; profitability
  claims are confined to specified pending-order attack sequences.
- AppTest initially hung creating an asyncio socket pair because the sandbox
  blocked loopback sockets. A diagnostic stack trace identified this; rerunning
  with permitted loopback access passed both dashboard tests in 31.98 seconds.
- Initial in-progress research batches were interrupted to add explicit capital
  efficiency metrics, per-wallet positions and source hashes before collecting
  the final report data. Their manifests record interruption; they are not used
  as completed findings.
- The complete suite then passed **44 tests in 55.68 seconds** with loopback
  access. Browser inspection confirmed the local app rendered; replay refresh
  was adjusted to run only during playback, and header spacing was increased for
  the narrow in-app browser view.

Later completed validation and actual research runs are recorded in the saved
results manifests and final findings. No observed test failure is suppressed.

## Completed research

- Pilot: 2,400 matched-model market runs, 4.8 million demand events, 100 seeds,
  all six scenarios on both comparison bases; completed in 382.68 seconds.
- Longer baseline: 400 market runs, 4 million events, 100 seeds, both bases;
  completed in 335.24 seconds. Concurrent runtimes include contention.
- Both manifests are complete. Source hashes were verified before generating
  the findings report and standalone interactive charts.
- Exact stress tables and 36 executed scaling markets supplement those batches.
- A CLI single-run export was executed and wrote a valid ZIP with config,
  metrics, prices, history, trades and wallet records.
- Deprecated Streamlit sizing arguments were replaced with `width="stretch"`;
  both app tests passed again in 19.01 seconds. This also removes repeated
  warnings observed during browser verification.
- Explicit play, pause and exact one-event stepping assertions passed in a final
  targeted app run: **2 tests in 10.61 seconds**. The wallet group chart displays
  only additive realized/marked P&L; incompatible individual first-exit quotes
  remain labeled in the wallet table.

## Phase 2 — 29 October 2026

- Wrote `PHASE2_DESIGN.md` before alternative-engine implementation. Preserved
  all eight historical engine files, verified both manifests, recomputed the old
  summaries and reproduced 84 saved market runs; see `PHASE1_AUDIT.md`.
- Found and fixed the fast constructor's <=1e-9 underfunding tolerance. The
  historical default runs did not use that input branch. Historical data and the
  original release ZIP were retained.
- Added an exact rational bounded potential/factory/ledger, a validated float
  implementation, fixed-cap normalization, a weighted inventory pool, isolated
  hub control, Decimal AMM calculations, paid inventory admission and finite
  external-market arbitrage. No dashboard rebuild was required.
- The complete suite passed **96 tests in 55.47 seconds**, with no skips or
  failures. Additional tests cover denomination invariance, convexity, attack
  formulas, cash limits, stock/depth limits and matched funding/starting prices.
- Main Phase 2 batch completed **1,000 markets / 300,000 demand events** (50
  seeds, five scenarios, four architectures), in 507.32 seconds. Source hashes,
  complete status and all seed summary distributions were independently checked.
- Added controlled actual/joint depth, toxic inventory, external arbitrage,
  fixed-shape bounded scaling and 20 executed scaling markets through 1,000 tokens.
- A larger exact bounded attack retained positive profit after 0.3% fees and
  passed a 1% victim payment cap; the ledger's rational invariants passed.
- Reproduced 60 terminal states and executed 120 retail portfolio exits to
  distinguish reference marking from actual cash realization. The first exit
  caller requested an entire float holding that exceeded the pool's computed
  remaining supply cap by a few ulps; the strict engine correctly rejected it.
  The caller was corrected to respect the actual cap and record, rather than
  erase, residual ownership. Maximum recorded dust: 1.6653345369377348e-16 of
  authorized supply. All corrected exit cash/ownership assertions passed.
# Copycat diversion study — 29 October 2026

Added an independent-curve routing/election research package under
`bonding_lab/copycat/` and reproducible experiments under
`research/copycat_diversion/`. The completed main study covers 322 settings,
45,412 retained market calls and 8,923,360 organic arrivals, with held-out
confirmation on 30 fresh seeds. It preserves buyer ownership by default for
leader-token purchases and tests treasury/lock/literal-burn sensitivities.

The new study audits exact cash routing, leader capture, spam, evasion, flipping
and pending-diversion front-runs. Stronger voluntary-portfolio controls remove
an apparent copy-spam uplift; strict badge controls correct favorable original
fallback before a leader qualifies. All source versions and superseded data are
labeled. The existing dashboard was unchanged. See the study's `DEVELOPMENT.md`
for the funding-boundary repair and the verified 138-test record, and
`FINDINGS.md` for the qualified economic verdict and reproduction commands.

