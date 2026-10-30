# Shared Bonding Lab and memecoin anti-vamp research

**Current goal:** reduce copycats splitting one meme's early attention and liquidity. Keep launching open, group related coins for discovery, and let buyers explicitly choose a clearly identified original/canonical mint.

Start with [the goal, approach, and complete research record](ANTI_VAMP_RESEARCH.md). The latest synthetic study covers 11,700 worlds on 100 paired seeds. Original-first routing raised the original's minute-15 buying share from 25.3% to 51.1% under default assumptions; the tested market-cap election could be captured by a funded copy. Canonical identity and real buyer adoption remain unresolved.

[Follow-up source, evidence, tests, and interface preview](research/anti_vamp_consolidation/README.md) accompany the existing four-mechanism and shared-curve studies below. This is off-chain research, not a deployed launchpad.

---

# Shared Bonding Lab

**Phase 2:** [audit](PHASE1_AUDIT.md), [mathematical design](PHASE2_DESIGN.md),
[executed findings](PHASE2_FINDINGS.md), and [research commands](PHASE2_README.md).
This adds bounded coupling, a paid-inventory shared AMM, finite external markets
and matched-capital tests without rebuilding the dashboard. Historical Phase 1
results below retain their original scope; their source snapshot is preserved.

An off-chain research simulator for the specified quadratic shared bonding
surface. It implements a precise Decimal reference ledger, a validated float64
Monte Carlo engine, synthetic agents, exact attack scenarios, and a Streamlit
research dashboard. It contains no wallets, contracts, or real transactions.

Read [MATHEMATICS.md](MATHEMATICS.md) for proofs and definitions and
[RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md) for executed results and limitations.
The recorded study completed 2,800 Monte Carlo market runs and 8.8 million demand
events, plus exact stress analyses and scaling simulations. The complete test
suite passed 44 tests. Coupling did not improve fixed-quantity self-price depth;
funded accounting remained solvent while cross-token ordering transfers were
possible. See the report for the conditions and measured distributions.
Synthetic outcomes are not historical data or investment advice. The independent
baseline is this same quadratic curve at lambda=0, not a calibrated Pump.fun model.

## Setup (Python 3.12+)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

On macOS/Linux use `python3.12 -m venv .venv` and `.venv/bin/python`.
If Windows' `python` alias opens the Store, use an installed Python executable.
For this workspace the bundled Python executable is recorded in
`results/environment.json`; the local `.venv` is already prepared after successful
installation. `requirements-lock.txt` records the actual installed environment.
For exact package versions, install with `python -m pip install -r requirements-lock.txt`.

## Reproduce research

```powershell
# One replayable run; CSVs/config/metrics packaged together
.\.venv\Scripts\python.exe -m bonding_lab.cli run --events 2000 --out results/scratch/run

# Matched models, six scenarios, both supply/capital bases, A-H tables
.\.venv\Scripts\python.exe -m bonding_lab.cli research --seeds 100 --events 10000 --out results/reproduction

# Larger research batch (long-running; results written after each scenario/basis)
.\.venv\Scripts\python.exe -m bonding_lab.cli research --seeds 1000 --events 10000 --out results/large

# Targeted faster batch
.\.venv\Scripts\python.exe -m bonding_lab.cli research --scenarios popular crash --bases equal_supplies --seeds 100 --events 10000 --out results/targeted
```

See `python -m bonding_lab.cli --help` and subcommand help for settings.
Saved manifests record configuration, package versions, seed range, elapsed time,
completion state and failures. Interrupted batches must not be interpreted as
complete. Changing options requires a new output directory to preserve provenance.
Quantities are abstract comparable units; p0=.01 USDC/unit and k=.0001
USDC/unit^2 are research defaults, not empirical estimates.

## Dashboard workflow

Configure token count, coupling, uniform or per-token funded starting supplies,
reserve capital, curve coefficients, population mix, trade notional, pressure,
volatility, duration, fees, seeds and attack settings. Run a simulation, inspect
the transaction replay, compare paired models, run stress tables, then download
data. Simulation controls create fresh fixed-parameter runs. Replay is a view of
completed transactions: it does not modify the market or claim live execution.
Larger Monte Carlo jobs run through the CLI to avoid blocking the dashboard.

## Project structure

```
bonding_lab/engine.py       Decimal reference, factory, wallet ledger, invariants
bonding_lab/fast.py         O(1) float64 trade and quote engine
bonding_lab/agents.py       Reproducible shocks and explicitly synthetic policies
bonding_lab/simulation.py   Scenarios, matched comparisons, replay and exports
bonding_lab/attacks.py      Exact frontrunning and coordinated wallet experiments
bonding_lab/experiments.py  Experiments A-H, seed summaries, provenance
bonding_lab/cli.py          Local research commands
dashboard.py               Interactive Streamlit laboratory
tests/                     Accounting, properties, parity, attacks and app tests
results/                   Actually executed research artifacts and manifests
```

## Interpretation

Starting supplies are fully backed by explicit genesis contributions attributed
to their holders, on top of trading cash. Extra starting reserve is a donation,
not spendable liquidity or a hidden creator allocation. Fees are never backing.
Wallets cannot borrow or short. Most random sell intentions target a random token;
an unowned position is skipped. The bank-run policy selects the largest available
position. Dedicated exact bank-run tables fully redeem every token.

Agents include retail, whale, momentum, holder, creator, sniper, bundler,
coupling-follower/MEV and adversary policies. Fractions govern retail and whales;
remaining agents cycle through the seven other roles. A very small population
need not contain every role. A creator has no privileged mint access. Coupling
followers alone are not claimed to earn arbitrage profits; explicit pending
victim transactions are modeled separately. All behaviors and ordering choices
are assumptions. Fixed random tapes match intentions, not necessarily fills.

Slippage means gross average execution price versus pre-trade marginal price;
price impact means the change in the marginal price. Both exclude fees in charts,
while cash, realized P&L and victim payment caps include fees. Wallet marked P&L,
first-exit liquidation P&L, collective redemption, treasury, buffer and backing
are labeled separately. Summing first-exit quotes overstates collective proceeds.

## Development stages

The separate [copycat-diversion study](research/copycat_diversion/README.md) reuses
the independent curve engine to test ticker leaders, buyer-owned routing, cash
payouts, burn/treasury interpretations and five adaptive attack classes. Its
[design](research/copycat_diversion/DESIGN.md) and
[findings](research/copycat_diversion/FINDINGS.md) include seeded reproduction
commands. This off-chain study does not change the existing dashboard.

1. Reference accounting and property tests precede dashboard development.
2. Float64 parity and synthetic scenarios validate the larger research path.
3. App tests exercise controls and exports; browser inspection verifies layout.
4. Only completed experiments enter the findings report. Failures and repairs
   are recorded in `DEVELOPMENT_LOG.md`.

Proposed mitigations (capped coupling, cohorts, private ordering, alternative
potentials) are discussed in the report; they are not silently substituted for
the original model.

Tests use the documented [Streamlit AppTest API](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
and [deterministic Hypothesis settings](https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html).
