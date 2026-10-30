# Bounded narrative-consolidation evidence bundle

**Revision note:** this directory preserves the first completed 10,000-world run.
Its `D_REFUSAL` setting had an ownership error: refusing creators still put seed
cash into platform escrow. The authoritative corrected run and final findings
are in `corrected_v2/`; it repeats the same frozen configurations/policies/seeds.
See `refusal_correction_record.json` and the corrected run's hash comparison.

The completion authority is `confirmation/manifest.json`, not this index. The
full requested matrix is frozen in `frozen_plan.json` before confirmation: 88
no-attack settings and 12 non-abstaining trained-policy settings, each evaluated
on seeds 10000–10099. There are ten candidate identities and 480 common latent
opportunities per seed. The primary close is 30 minutes with seven days follow-up.

The model is synthetic. No historical calibration, contracts, wallet connections,
real funds, purchased data, new dependencies or dashboard are involved.

## Evidence map

- `preservation_before.json` / `preservation_after.json`: hashes of all 465
  preexisting source, document and research files; generated environments/caches
  and temporary directories are excluded. Git remains unborn and unmodified.
- `IMPLEMENTATION.md`: financial rules, quantization, assumptions and development
  repairs. The original four design documents remain unchanged.
- `arithmetic_witnesses.json`: actual integer-ledger values for the required
  adverse zero-fee examples. Unrounded and randomized parity checks are in tests.
- `gate*/`: separate test logs/XML/manifests, including failed development gates.
  The final pre-freeze complete suite has 195 tests: 138 existing plus 57 new.
- `pilot/`: 180 executed development worlds on seeds 0–19, runtime/variance
  measurements, and the 56-case funded ordering grid.
- `training/`: 4,600 exported rows and source from the interrupted pre-confirmation
  search, retained for audit. Not used for final policy selection.
- `training_final/`: 6,650 complete policy/world evaluations on seeds 100–149,
  all candidates and final selections. Abstention is eligible in every family;
  independently optimized A controls are included.
- `frozen_plan.json`: exact configurations, policies, source hashes, planned
  cells and confirmation seeds. Source-changing runs require a new freeze.
- `confirmation/`: raw seed/checkpoint rows, all tapes and tape/outcome hashes,
  representative complete traces and terminal wallets for seed 10000 in every
  treatment, source snapshots, progress, failures and completion status.
- `analysis/`: distributions, paired bootstrap intervals, acceptance grids,
  attack P&L/funding/user-loss tables, unlock observations and completed matrix.
- `NARRATIVE_RESEARCH_FINDINGS.md`: generated findings for this completed bundle.

## Reproduce

From the original research workspace, use its existing `.venv` Python executable.
Choose a new directory: existing run folders are never silently overwritten.

```powershell
.\.venv\Scripts\python.exe -m bonding_lab.narrative init --root research/narrative_consolidation/reproduction
.\.venv\Scripts\python.exe -m bonding_lab.narrative.test_runner --scope all --out research/narrative_consolidation/reproduction/tests
.\.venv\Scripts\python.exe -m bonding_lab.narrative pilot --root research/narrative_consolidation/reproduction
.\.venv\Scripts\python.exe -m bonding_lab.narrative train --root research/narrative_consolidation/reproduction
.\.venv\Scripts\python.exe -m bonding_lab.narrative freeze --root research/narrative_consolidation/reproduction
.\.venv\Scripts\python.exe -m bonding_lab.narrative confirm --root research/narrative_consolidation/reproduction
.\.venv\Scripts\python.exe -m bonding_lab.narrative report --root research/narrative_consolidation/reproduction
.\.venv\Scripts\python.exe -m bonding_lab.narrative verify --root research/narrative_consolidation/reproduction
```

Existing Streamlit regression tests require local loopback socket access. The
simulation and study do not require external network access. A report is written
inside its study folder; reproductions do not overwrite an existing top-level
findings document. The example test output folder is new in a new reproduction.

## Replay an arbitrary confirmation seed

```powershell
.\.venv\Scripts\python.exe -m bonding_lab.narrative replay --root research/narrative_consolidation/bounded_study --name C --seed 10037 --out research/narrative_consolidation/replay_C_10037
```

Replay uses the stored tape and frozen policy/configuration, verifies the exact
stored outcome hash and exports cash, claim, ranking, settlement and refund
events. Conditional receipt authorizations are in the trace; post-election route
decisions are reproducible from the stored opportunity tape and code, rather
than every refusal having a separate trace row. The saved source must match the
frozen version. Native price/attention preferences are behavioral floating-point
calculations; financial feasibility, fees, quantities, transfers, settlement
limits and conservation are integer decisions.

## Interpretation boundaries

Seed confidence intervals condition on the synthetic population and policy class.
They do not quantify uncertainty about real adoption, elasticity, genuine demand
or creator participation. The future-choice benchmark is neutral latent offered
quote, not an observable production identity or guaranteed future funded demand.
Creator refusal is an exogenous outside-option stress, not a solved entry
equilibrium. The arbitrageur role has no profitable fungible countervenue in
this bounded world. Secondary prelaunch price manipulation is unavailable in D;
funded same-token ordering is tested separately. No leverage, creator bribes,
unbounded coalition search or production security proof is claimed.

Compare cohort capital, private depth and activity together. Market cap and a
winner's share alone are insufficient. Support locks/destruction and D's cash
waiting change ownership/exit rights; neither creates permanent LP capital.
