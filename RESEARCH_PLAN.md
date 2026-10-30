# Narrative consolidation research plan

30 October 2026. **Current scope: Phase 1 only.** The four design documents are
research specifications. New A–D models, new Monte Carlo comparisons, dashboard
features and `NARRATIVE_RESEARCH_FINDINGS.md` are not claimed complete. The new
study is separate from the repository's earlier work also called Phase 2.

## 1. Repository audit and preservation

Inspected the original Decimal/float execution engines, agent tape, experiments,
independent-curve copycat routing/election/market/attack code, tests, dashboard
tests, mathematical audit, earlier Phase 2 design/findings and copycat findings
including the any-winner reanalysis. Reusable components and limits are mapped in
`PRIOR_ART.md`. Existing grouping and fixed behavioral assumptions are not silently
promoted to validated narrative identity or user consent.

The repository has an unborn `master` branch with no commits; its preexisting
project files are untracked. Consequently `git diff` alone cannot establish
preservation. Before adding documents, a SHA-256 inventory captured 445 original
files (173,107,085 bytes), including source, research, recorded results and ZIP
archives. It excludes environment, caches, temporary files and generated package
metadata. The final validation compares every inventoried file's bytes. No old
model, result, dependency or dashboard file is edited.

Evidence lives in `research/narrative_consolidation/phase1/`:

- `preservation_manifest.json`: original-file SHA-256 hashes and environment.
- `baseline_pytest.xml` and `baseline_summary.json`: actual existing-suite result.
- `run_baseline.py`, `baseline_run.json`, `baseline_pytest.log` and
  `baseline_progress.jsonl`: reproducible runner and per-test diagnostic evidence.
- `probe_public_data.py` and `data_access_probe.json`: reproducible read-only
  public-data access attempt, with raw successful responses and no calibration.
- `validate_phase1.py` and `phase1_validation.json`: exact arithmetic witnesses,
  documentation links, baseline gate and original-file preservation checks.

Baseline command from repository root, using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=.tmp/narrative_baseline_pytest.xml
```

The initial default-temp attempt was interrupted after 102 tests completed and
did not produce a final XML. Collection separately found 138 tests. A diagnostic
retry with workspace-local temporary files localized the stall to Streamlit's
asyncio loopback socket creation. Its trace and completed-test log remain in
`sandbox_blocked_pytest.log` and `sandbox_blocked_progress.jsonl`. The unchanged
suite passed with local socket access: **138 passed, zero failures/errors/skips**
in 63.447 seconds according to the JUnit suite timer. XML/logs are saved directly
to this evidence directory. Phase 1 arithmetic, document and preservation checks
also pass; all 445 inventoried original files are unchanged. Historical README counts
refer to older stages. This baseline is not a rerun of all historical economic
batches or a deployed-protocol audit. Reproduction commands are:

```powershell
.\.venv\Scripts\python.exe research/narrative_consolidation/phase1/run_baseline.py
.\.venv\Scripts\python.exe research/narrative_consolidation/phase1/probe_public_data.py
.\.venv\Scripts\python.exe research/narrative_consolidation/phase1/validate_phase1.py
```

## 2. Unresolved assumptions and implementation decisions

These are uncertainties to expose, not reasons to assume success or require a
new round of user approval. The defaults in `MECHANISM_DESIGNS.md` let later
implementation proceed without pretending empirical questions are resolved.

| ID | Unresolved issue | Starting rule / required falsification |
| --- | --- | --- |
| U1 | Will B buyers voluntarily buy A? | Acceptance and outside options depend on type/price; sweep zero to one. No universal threshold inferred from prior routing study. |
| U2 | Does the title attract extra attention? | Primary effect zero; test positive/negative feedback separately with finite budgets. |
| U3 | Will losers migrate? | Zero participation control; price-sensitive consent and actual proceeds, never market cap. |
| U4 | Can the group be defined fairly? | Frozen admitted cohort plus false-positive/negative contamination stress; operators have no right to seize funds. |
| U5 | Which score predicts future demand? | Highest score and evaluator-only future-demand benchmark separate; scores may choose wrong. |
| U6 | Is locked cash a costly signal? | Count elapsed capital-time and opportunity cost; compare refund-only support, compatible settlement and actor concentration. |
| U7 | Will losing creators participate? | Fund outside-option launches; model refusal, promotion costs and fee-sharing sensitivities. No free acquisition of their traffic. |
| U8 | Is reserve concentration durable? | Measure absolute winner and cohort reserves/depth after selling and through 7d. No permanent LP claim. |
| U9 | Is long-horizon behavior plausible? | Explicit attention decay/revival and finite remaining cash; no empirical calibration yet. |
| U10 | Does selection fit every instrument? | D cap/volume/holder scores N/A; commitment overlays in A–C must be funded in all comparison worlds. |
| U11 | Who knows the close? | Fixed, honest hidden, insider-known, biased draw and withheld reveal are separate cases. |
| U12 | Does D benefit only from lockup/batch launch? | Matched single-candidate batch and lockup controls; same post-handoff market, no prelaunch spot assets. |
| U13 | How much depends on curve shape? | Primary independent linear curves; price/capital/denomination controls and separate finite-inventory sensitivity. |

Defaults exclude leverage, arbitrary token transfer taxes/rebases, cross-chain
conversion and automatic irreversible loser conversion. They can be researched
only with explicit account/consent/debt extensions. No assumption here establishes
production feasibility or acceptance rates.

## 3. Separate implementation layout and stage gates

Future code belongs under `bonding_lab/narrative/`, with tests under
`tests/narrative/`, configurations and run artifacts under
`research/narrative_consolidation/`. Keep existing source unchanged unless a
separately tested shared utility extraction is necessary. Proposed modules:
`ledger`, `markets`, `architectures`, `settlement`, `election`, `demand`, `agents`,
`attacks`, `experiments` and CLI. A proposal is not an existing command.

| Phase | Work | Gate before following phase |
| --- | --- | --- |
| 1 | Audit, primary-source comparison, ownership/settlement specification, assumptions and baseline | Existing suite passes; preservation and arithmetic validation passes; data status explicit; four documents complete |
| 2 | Common reference ledger; A–D and S1/S2/S3; fee support, escrow, cancellation, timeout and refunds | Exact/quantized accounting properties; full liquidation; repeated/refused claims; no-winner tests; float parity; deterministic financial traces for every architecture |
| 3 | Finite funded agents, latent narrative opportunities, acceptance/outside choices, elections | Same pre-policy tape hash across models; sybil budget property; no future information; wrong-winner examples; zero-feedback/zero-acceptance controls; fixed and random close replay |
| 4 | All attack families below and constrained policy optimization | Complete-exit P&L/cost reconciliation; feasible oracle-information limits; held-out seeds; independent-control policy search; profitable counterexamples sought |
| 5 | Controlled Monte Carlo, uncertainty, acceptance thresholds and robustness | Completed manifests for declared matrix; invariant failures retained/repaired; no pooling repeated seeds/policies; main conclusions survive specified controls or are rejected |
| 6 | Dashboard/replay and findings report | Dashboard consumes validated ledger outputs; UI tests/replay parity; report tables reproduce from completed artifacts |

Re-run the existing suite at each code-changing gate. Do not mark later phases
complete based on design documents, smoke runs, successful UI rendering or
supported CLI flags. If a run fails, keep the failure and source snapshot before
repair; reruns use a fresh named bundle.

## 4. Threat matrix and required outputs

| Attack/scenario | Decision variables and comparison |
| --- | --- |
| 1 Whale wins then dumps | Candidate, buy size/timing, aliases, residual and exit schedule; compare title capture and ordinary early trading |
| 2 Coordinated metric capture | Wallet splits, thresholds, lock duration and concealed ownership; fixed actor capital |
| 3 Wash ranking | Round-trip count/size, rebates, fee beneficiary and funding reuse; actual unrecoverable costs |
| 4 Creator spam | Candidate count, launch cost, promotion allocation and recognition evasion; demand denominator includes all spam |
| 5 Cross-narrative contamination | False metadata/group assignment and entry timing; no access to unconsented reserve |
| 6 Legitimate creator misgrouped | Lost choice, refusal, refunds, outside venue and creator welfare |
| 7 Exit rush | Time to close, belief updates, S2 redeemable versus locked claims, synchronized and staggered exits |
| 8 Migration frontrun | Pending batch size, capital, victim output cap and execution order; include failed attacks and protected batches |
| 9 Price manipulation before conversion | Thin secondary venue, funded spot distortion, reference/TWAP bounds and fallback; primary D prelaunch venue N/A |
| 10 Losing creator refuses | Outside-option quality, expected fees, launch/promotional expense; count absent launches/traffic |
| 11 Winner popularity collapses | Common demand shock immediately after close; independent control and alternative true-demand winner |
| 12 No qualified candidate | Empty/tied/underfunded cohort, incompatible escrow, withheld reveal and timeout; exact refunds |

Each row exports actor peak capital at risk, acquisition principal, total fees,
realized/unrealized P&L, feasible complete-exit cash profit or residual inventory,
other-participant paired losses, per-market reserves and winner capital remaining.
Nonfinancial shocks have a no-attacker label and zero attack-profit statistics,
not a fabricated malicious P&L. Attack cost includes promotion, launch, network
and funded capital-time expense separately from recoverable principal.

Search time/size/exit/candidate/alias policies over feasible capital ranges; include
abstention, grid search and local refinement. Use finite shared funding, actual
countervenue depth and action costs. Freeze best policies after training, test on
unseen seeds and report the best found attack within the disclosed class. Tune
an attacker independently in A too. A finite failed search cannot prove safety.

## 5. Matched demand and experiment design

Counter-based or separately keyed random streams for narrative attention,
candidate quality/loyalty, actor endowments, execution ordering, acceptance and
attacker choices prevent additional rejected actions from shifting every later
draw. Keys include seed, actor, opportunity and stream name. Same opportunities
and outside budgets apply across worlds; realized fills and subsequent balances
can differ. Demand is not replenished when a trade is rejected or a whale exits.

Candidate choice uses frozen synthetic utility coefficients plus endogenous
prices/history. Export the coefficients. Future-demand oracle calculations are
evaluation-only and use untouched future opportunities under neutral exposure;
do not make the favored candidate win by construction. Creators influence
visibility only through a declared response to paid promotion, not free social
impressions converted to buyers.

Stage 5 matrix includes all candidate counts 2/5/10/25/50/100 and election windows
2/5/15/30 minutes, low/high total demand under **fixed total** funding, popularity
and decay, creator concentration, whale share, acceptance, migration participation,
fees, depth and creator incentives. Hold numerical event resolution constant in
economic time around elections; reducing events for speed is a separate study.
Use full 7-day simulated timestamps with fine close resolution and coarser
event-driven follow-up where validated; report events as well as elapsed time.

Proposed main factorial spine: six counts × four windows × two demand levels ×
eleven acceptance levels (0,.1,...,1) = 528 cells per applicable architecture/rule.
Acceptance is N/A in A/B rather than 11 duplicate independent observations.
Add one-factor sweeps, preregistered interactions and joint worst cases instead
of claiming a full cross-product of all knobs. Candidate counts and attention
increase separately: more tokens never automatically multiply total demand.
Report the actual executed cell count and seed count for every result.

Proposed seed partition: development 0–19; attack training 100–149; screening
1000–1099; final confirmation 10000–10499. These are planned ranges, not executed
runs. Pilot cost and variance before fixing confirmation budget. If a run is
too costly, narrow the declared question or report an incomplete matrix; do not
quietly replace 500-seed claims with smoke results. Preserve raw seed outcomes,
failed-run counts, full configurations, software versions, source/tape hashes,
wall time, search candidates and completion status.

Compute paired seed differences, medians, 5/25/75/95 percentiles, drawdowns and
worst observed tails. Bootstrap paired seeds for effect/threshold uncertainty;
use Wilson intervals for profit frequencies. Wallets in the same world are not
independent seeds; duplicate cached runs add no sample size. Treat extensive
ranking as exploratory and use untouched confirmation for selected claims.
Intervals describe the assumed model, not real-market parameter uncertainty.

## 6. Metrics and decision criteria

Primary endpoints are winner **and cohort** retained trading capital, executable
sell depth at 1/5/10% impact, organic funded activity and participating actors
at +1h/+24h/+7d. Report fee-inclusive buy/sell slippage, abandoned quote, accepted
routing by count and quote, voluntary migration by eligible claims and actual
recoverable collateral, creator participation/realized cash outcomes, trader
realized P&L distributions and separately marked positions. Include gross flow,
net deposits, reserves, fees, escrow and any LP claims as distinct columns.

For equal capital, compare A–D under the same endowments, launch costs, curve
parameters, promotion response and economic horizon; disclose where D's initial
state differs. Evaluate a common candidate identity using a frozen neutral
benchmark and the best realized token too, so selection-conditioned winner
comparisons do not overstate performance. A chooses no official winner.

Estimate acceptance break-even per setting using paired capital/depth outcomes.
Use the analytical decomposition in `ECONOMIC_INVARIANTS.md` as a check, then
refine the acceptance grid only on development data and confirm held out. A
positive effect at one acceptance rate is not a universal threshold; nonmonotonic
effects or no crossing must be reported. Separate reserve gains due to involuntary
lockup from gains after all voluntary exit windows.

Reject a proposed variant if its apparent gain requires double-counting capital,
incompatible ownership, unbounded external demand, hidden subsidized inventory,
unfunded creator cooperation or an unverifiable identity oracle. Reject a broad
economic advantage if plausible acceptance/loyalty/creator assumptions yield
inferior cohort retention or organic survival, if profitable capture overwhelms
any depth improvement, or if improvement disappears against a matched voluntary
single-token/batch control. A larger winner share alone cannot pass.

Later `NARRATIVE_RESEARCH_FINDINGS.md` must answer all ten questions in the brief:
retention, executable depth, survival versus cap, robust selection, acceptance
break-even, profitable capture, loser treatment, creator incentives, equal-capital
architecture ranking and rejection conditions. For every answer distinguish
proof/arithmetic, synthetic completed evidence, empirical observation and unknown.

## 7. Historical data work and dashboard prerequisites

The Phase 1 access probe is discovery only; collection methods, zero paid spend,
request failures and unavailable fields are documented with the raw responses.
The network retry obtained two 30-pair keyword snapshots after sandbox DNS
failures; neither establishes a complete historical cluster or unique people.
No historical behavioral estimates are imported. Further historical work requires
mint-level cluster labels, launch and pool-migration times, deduplicated reserves,
decoded quote flows, holder/creator concentration and survival windows with dead
tokens retained. Record provider pricing/access scope before any paid collection.
Fit only supported parameters, carry missingness/identity ambiguity, and keep a
synthetic path when reliable coverage is unavailable. Historical correlations
cannot show that this mechanism would have caused better outcomes.

Only after validated models, extend the existing dashboard with a separate
narrative tab: group/candidate creation; behavior/window/rule controls; replayed
rankings and finalization; explicit capital-flow and migration ledgers; attack
replay; A–D comparisons; seed distributions and depth/retention charts. Replay
must show actual timestamped authorization, refunds, no-winner and abandoned
orders. Display simulated time and assumptions; do not label replay as live
on-chain execution. Keep old dashboard tests and workflows passing.
