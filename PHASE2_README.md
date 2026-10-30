# Phase 2 research workflow

Read [PHASE1_AUDIT.md](PHASE1_AUDIT.md) and [PHASE2_DESIGN.md](PHASE2_DESIGN.md)
first. The design was written before the new engines. The final executed results
and verdict are in [PHASE2_FINDINGS.md](PHASE2_FINDINGS.md).

The existing Streamlit dashboard is unchanged. Phase 2 is a CLI research workflow
with CSVs, manifests, exact accounting tests and standalone interactive figures.

```powershell
# Existing virtual environment; fresh setup is in README.md
.\.venv\Scripts\python.exe -m pytest -q

# Audit the original manifests/results using their preserved source
.\.venv\Scripts\python.exe scripts/audit_phase1.py

# Reproduce the recorded Phase 2 study in a new output directory
.\.venv\Scripts\python.exe -m bonding_lab.phase2 --seeds 50 --events 300 --out results/phase2_reproduction

# Larger supported batch (not implied to have been executed)
.\.venv\Scripts\python.exe -m bonding_lab.phase2 --seeds 100 --events 1000 --out results/phase2_large

# Individual scenarios, different budgets, fees or number of assets
.\.venv\Scripts\python.exe -m bonding_lab.phase2 --seeds 20 --events 500 --scenarios divergent toxic_admission --capital 10000 --tokens 10 --fee 0.003 --out results/phase2_targeted

# Regenerate the report from the completed original Phase 2 output
.\.venv\Scripts\python.exe scripts/verify_phase2_exits.py
.\.venv\Scripts\python.exe scripts/build_phase2_report.py
```

`python -m bonding_lab.phase2 --help` lists available options. More assumptions
are explicit in frozen `Study` configuration objects for Python-driven research.
The output directory must be new or empty. Failures preserve a failed manifest;
interrupted output must never be presented as a completed batch.

## Source modules

- `phase2/surfaces.py`: independent/quadratic/bounded potentials, immutable asset
  metadata, exact rational funded wallet/factory reference, validated float engine,
  price/capital calibration and exact finite-difference ordering profit.
- `phase2/amm.py`: weighted common-cash pool, isolated USDC hub control, simple
  declared admission checks and a conservatively rounded Decimal reference.
- `phase2/external.py`: independent finite-dealer quotes with window depth,
  persistent inventory and persistent cash.
- `phase2/world.py`: fully accounted genesis funding, positions, trading,
  cash-limited two-leg arbitrage and paid finite toxic-creator inventory.
- `phase2/research.py`: matched shocks, static/joint depth, manipulation,
  toxic inventory, scaling, external-arbitrage controls and uncertainty summaries.

## Accounting/data dictionary

All economic token quantities are fractions of the immutable verified authorized
cap. A full claim's initial reference price is $10,000; this is a synthetic unit
choice, not the price of one raw memecoin. Fractions/atomic amounts transform
together under redenomination, and this invariance is property-tested.

Primary sponsor net deployment is $10,000 in each design. Each world additionally
has the same paid dealer seed inventory ($1,000), dealer capital ($100,000), retail
capital ($20,000) and bot capital ($5,000). Total starting USDC is $136,000. Curve
backing starts at $11,000; AMM cash starts at $5,000 plus $5,000 of paid inventory.
Each world has a sponsor, finite dealer across the reference markets, one aggregate
retail wallet, an atomic arbitrage wallet, a creator and a network-expense account.
The design document traces the dealer's secondary purchase, sponsor cash left,
creator proceeds, and every balance. No inventory is free to the LP or dealer.

The creator's remaining AMM tokens are a finite authorized issue, not a promise of
USDC redemption; curve tokens are funded redemption claims and cannot be freely
minted by that creator. The different claims/equity rights are a material
comparison limitation. Equal deployed cash budgets do not make the instruments
economically identical or imply equal total FDV of undeployed creator stock.

- `initial_genesis_mark_gain` is separated from subsequent sponsor P&L.
- `sponsor_mark_change` measures wealth change after initialization at external
  marks; `sponsor_pnl_vs_paid` also includes the initial mark/cost difference.
- Curve `operator_fee_income` is actual USDC in a separate treasury. It excludes
  backing, whose redemption liabilities offset collateral.
- `lp_nav`, `lp_pnl`, `lp_loss_vs_hodl` apply only to inventory AMMs. N/A for curves
  is intentional; there is no fabricated LP claim on locked curve collateral.
- Pool `fee_value_at_execution` values retained input fees at the *internal
  pre-trade spot quote*. It is an inventory accounting diagnostic, **not realized
  USDC fee income**, and can greatly overstate a toxic token's outside value. LP
  NAV uses independent reference marks and is the profitability measure.
- `arb_profit` is realized cash gain after trading fees and network expense.
  Both legs must be funded and inventory-feasible. Simulation assumes atomic
  execution without latency; it is not a real mempool profitability estimate.
- `backing_shortfall` and `backing_absolute_error` apply to surfaces. The AMM
  promises pro-rata inventory, so a lower LP dollar NAV is not recorded as a
  breach of a nonexistent fixed-dollar redemption obligation.
- `cash_depletion_fraction` is compared with each mechanism's own initial cash,
  while dollar cash, paid inventory cost and sponsor funding are also exported.
- `mean_path_mispricing` compares quotes to exogenous reference mids. A mid is
  not an unlimited executable market; depletion can leave no token inventory to
  take the apparently favorable external side.
- `executable_reference_notional_1pct` is common reference-dollar token quantity
  that can trade within a 1% execution deviation at the aligned initial state.
  The zero-fee table isolates depth; the fee-inclusive table includes costs.

Reference innovations are matched across architectures; executions change dealer
inventory and subsequent route feasibility. Curves use funded mint/burn; pool
trades use actual inventories. Global cash and ownership are scanned repeatedly.
Exact rational tests enforce equalities. Float tolerance is explicitly scoped to
research state accumulation; it does not waive intentional underfunding.

External reference quotes are synthetic. In particular, a frictionless market
would not persistently offer funded redeemable claims below an immediately
available redemption value. Our finite dealer can make such a loss-making quote,
then runs out of inventory; extraction can be the dealer's loss rather than a
curve reserve shortfall. The model does not prove a realistic equilibrium for
puttable claims, demand quality, arbitrary correlated returns or token values.

## Admission and adversarial scope

The bounded curve admits verified immutable supply metadata into a fixed-capacity
cohort at zero issued supply. No live coefficient normalization occurs. The AMM
uses fixed weights and paid seed positions; new tokens cannot attach to an old
cohort's cash. Known price/cap errors are rejected by the declared screening check.

The toxic scenario represents weak screening/future failure: a token initially
quoted at the common price collapses, and its finite creator stock is acquired
at that collapsed reference price and sold into the common pool. This private
OTC leg bypasses the public dealer's depth *explicitly*, pays the creator, and is
limited by actual creator stock and bot cash. Curves have no corresponding free
creator mint right. The isolated hub is a risk control with the same paid pool
inventory, not a claim that it shares financial liquidity between tokens.

Protocol/oracle implementation, token contract audits, admission attestations,
real exchange calibration, gas auctions, LP withdrawals during attacks, optimal
asset weights and permissionless safety are not established by this research.
The verdict distinguishes local depth from socialized losses and rejects paper
valuations as evidence of improved liquidity.
