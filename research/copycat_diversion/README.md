# Copycat diversion research

**Objective clarification:** success means convergence on whichever token wins,
including a copy. Start with [WINNER_REANALYSIS.md](WINNER_REANALYSIS.md). The
earlier original-focused verdict is not a verdict on that clarified objective.

Read [DESIGN.md](DESIGN.md) for the rules, exact accounting implications and
disclosed attack classes. [FINDINGS.md](FINDINGS.md) reports only completed runs.
The existing Streamlit dashboard is unchanged; this study is a CLI research task.

From the repository root (Python 3.12+ and existing dependencies):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/copycat -q

# Small functional workflow check, not evidence for the economic verdict
.\.venv\Scripts\python.exe -m bonding_lab.copycat --mode smoke --train-events 60 --screen-events 60 --screen-seeds 2 --confirm-seeds 2 --out research/copycat_diversion/reproduce_smoke

# Full recorded protocol in a fresh bundle; --workers changes execution only
.\.venv\Scripts\python.exe -m pytest -q --junitxml=research/copycat_diversion/reproduce/validation.xml
.\.venv\Scripts\python.exe scripts/copycat_parallel.py --out research/copycat_diversion/reproduce/results --workers 6
.\.venv\Scripts\python.exe scripts/copycat_controlled_attacks.py --out research/copycat_diversion/reproduce/controlled
.\.venv\Scripts\python.exe scripts/copycat_badge_controls.py --out research/copycat_diversion/reproduce/badge_controls
.\.venv\Scripts\python.exe scripts/copycat_confirmation_controls.py --study research/copycat_diversion/reproduce/results --out research/copycat_diversion/reproduce/confirmation_controls --all-controls --workers 6
.\.venv\Scripts\python.exe scripts/copycat_wallet_panels.py --study research/copycat_diversion/reproduce/results --out research/copycat_diversion/reproduce/wallet_panels --workers 6
.\.venv\Scripts\python.exe scripts/copycat_portfolio_controls.py --base research/copycat_diversion/reproduce --workers 6
.\.venv\Scripts\python.exe scripts/copycat_strict_badges.py --out research/copycat_diversion/reproduce/strict_badges --workers 6
Copy-Item research/copycat_diversion/DESIGN.md,research/copycat_diversion/README.md -Destination research/copycat_diversion/reproduce
# Choose the economic verdict only after inspecting the completed results.
.\.venv\Scripts\python.exe scripts/copycat_winner_reanalysis.py --base research/copycat_diversion/reproduce
.\.venv\Scripts\python.exe scripts/build_copycat_report.py --base research/copycat_diversion/reproduce --verdict not_viable
```

Output directories must be new or empty. Each has a configuration/source-hash
manifest and completion state; failed or interrupted experiments are not final
findings. The failed development search is preserved under `development/` with
its source and diagnosis. The original study uses `results/`; reproduction
commands deliberately choose other paths to preserve the evidence.
The report command records a research judgment; its verdict flag does not change
an experiment or statistic. Reassess the verdict if the assumptions change.

The original sequential command remains available:
`python -m bonding_lab.copycat --mode full --out <new-directory>`.
The process-parallel runner uses the same functions, candidates and seed protocol.
Its 12-row parity check matched serial output bit for bit. Identical evaluation
calls are computed once and copied; cache hits are not extra market executions
or statistical observations. The first 170 completed serial training settings
were source-checked, preserved and resumed in the production study.
The wallet-panel supplement compares the same individuals against their matched
control and reports individual tails. The portfolio-control supplement expands
zero-tax spam/evasion strategies to voluntarily buy leader tokens: this guards
against falsely calling an otherwise available portfolio trade a novel exploit.
Strict badge controls disable steering while no elected leader exists. Original
delayed-badge fallback records are preserved for audit, rather than used as
evidence of a badge before qualification. First-launch badge paths are unchanged.

Useful knobs:

```powershell
.\.venv\Scripts\python.exe -m bonding_lab.copycat --mode study --confusion 0.1 --informed 0.3 --attacker-capital 100000 --gas 0.05 --launch-cost 10 --out research/copycat_diversion/lower_confusion
```

`--mode full` tests a 144-setting leader/form/rate core, plus matcher/flip/cooldown
robustness at 5%, treasury ownership/redemption and literal-burn sensitivities,
matched no-diversion controls and badge controls: 322 distinct settings. It is
not the full cross-product of every possible knob. `study` narrows the robustness
cross-product and contains 244 settings. Window/rate levels are never pooled as
if they were one treatment. Badge shares are 25%,50%,75%; the no-badge control is
also present. Confirmation selects 12 finalists from the screen, without tuning
their attack policies on confirmation seeds.

## Files and interpretation

- `bonding_lab/copycat/reference.py` extends the existing Decimal ledger at λ=0.
  It audits exact routed spending, pro-rata cash transfers and funded destruction.
- `router.py` uses the existing `FastBook`, validates all funding and applies
  independent reserve differences. Representable quantities are rounded down
  when necessary to prevent the quadratic inverse from overdrawing a wallet by
  a floating-point ulp. Unspent numerical dust stays with its owner.
- `matching.py` and `election.py` implement disclosed matching, dwell, threshold,
  distinct-address windows and cooldowns. Addresses are not identities.
- `market.py` supplies seeded launches, organic/informed arrivals, snipers,
  coordinated buyers, a vamper, actor-controlled aliases and funded exits.
- `attacks.py` defines the finite policy classes, including abstention. `experiments.py`
  trains/evaluates them on separate seeds and exports every searched candidate.

Training uses seeds 11,22 and 160 arrivals; screening uses 100–105 and 240 arrivals;
confirmation uses 1000–1029 and 480 arrivals. All span 240 simulated minutes with
the same intended aggregate organic notional ($600k) and funded organic capital
($1m). Arrival resolution and per-arrival wallet capital differ by stage, so stages
are separate experiments, not pooled samples. The attacker has $1.1m across
funded aliases, never $1.1m per alias. Initial total cash is $2.225m in every world.

Buyer confusion, equal visibility of different spellings, informed behavior and
badge steering are assumptions. All near-ticker/evasive copies remain in the
semantic campaign denominator. The attacker cannot launch before the original
in the primary market. No real market data, identity attestations, transaction
latency, price discovery outside these curves or organic token utility is modeled.

Raw results contain one selected policy per family per seed, including idle when
it won training. Repeated idle policies are repeated evaluations of the same
seeded world, not additional independent evidence. Seed counts for an estimate
are the counts within that treatment/family. The same selected strategy also runs
under a matched no-diversion control. Positive copy-launch trading profit already
available in the control is not automatically a new diversion exploit.

Confidence intervals describe uncertainty within the assumed simulator. Mean
intervals use t critical values (including small screening n); profitability
frequencies use Wilson intervals. Worst-family ranking is a post-hoc stress
envelope across disclosed policies, not an omniscient deployable prediction.
No bounded search proves that an unobserved attack does not exist.

## Liquidity and profit definitions

The primary share measures actual private-holder net redemption on independent
curves, not marginal price × supply. For token i with pricing supply q and protocol
held quantity z, accessible private claims are `(1-f)[R_i(q)-R_i(z)]`.
Separate columns report absolute leader/original liquidity, total accessible
liquidity, donated literal-burn surplus, locked quantities and treasury quantities.
A higher share caused only by draining copies is not credited as new leader
liquidity. Distinct fields show the original group and attacker-led other groups.

“The leader” in headline identity metrics means the leader of the original's
matching group. Evasive groups can have their own attacker leaders; their shares
are reported separately and remain in all campaign-wide denominators. First-launch
selection identifies the original by construction here because pre-squatting is
excluded, not because a ticker proves authorship.

P&L is final cash minus funded initial cash after scheduled and terminal sales,
including curve fees, paid launch costs, network costs, cash dividends and creator
payments. Protocol burn/treasury inventory is excluded from user liquidation.
Remaining unprofitable-to-redeem dust is explicitly exported. Early/late cohorts
refer to the first/last third of arrivals; leader/copy labels refer to the intended
purchase at that moment. Buyer-owned diversion can give a copy buyer both assets.
Terminal wallet exit order is seeded; it is not assumed everyone exits first.

Direct cash received is separated from actor trading profit, and self-funded
diversion is excluded from “external attacker receipts.” Treasury that never sells
matches the buy-and-lock public path; its remaining redemption option is overhang
risk. Literal reduction of pricing supply instead retraces the price and retains
a surplus with no invented holder redemption right. Both interpretations are
reported rather than conflated.
