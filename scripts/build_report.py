"""Build findings only from completed, provenance-checked local research runs."""
from pathlib import Path
import hashlib
import json
import sys
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.attacks import bundle, frontrun


def money(x):
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def md_table(headers, rows):
    return "| "+" | ".join(headers)+" |\n| "+" | ".join(["---"]*len(headers))+" |\n"+"\n".join("| "+" | ".join(map(str,row))+" |" for row in rows)


def main():
    pilot = ROOT/"results/pilot"
    long = ROOT/"results/long_baseline"
    manifests = [json.loads((p/"manifest.json").read_text(encoding="utf-8")) for p in (pilot,long)]
    for manifest in manifests:
        if manifest["status"] != "complete":
            raise RuntimeError("Refusing to report an incomplete research batch")
        for path,digest in manifest["source_sha256"].items():
            actual = hashlib.sha256((ROOT/path.replace("\\","/")).read_bytes()).hexdigest()
            if actual != digest:
                raise RuntimeError("Research source changed: "+path)
    rows = []
    all_raw = []
    for scenario in manifests[0]["scenarios"]:
        for basis in manifests[0]["bases"]:
            stem = scenario+"_"+basis
            raw = pd.read_csv(pilot/(stem+"_runs.csv"))
            all_raw.append(raw)
            sums = pd.read_csv(pilot/(stem+"_summary.csv"))
            paired = sums[sums.model=="shared_minus_independent"].set_index("metric")
            shared = raw[raw.model=="shared"]
            attack = money(shared.attacker_profit.mean()) if scenario=="frontrun" else "n/a"
            rows.append([scenario,basis.replace("equal_",""),
                         money(paired.loc["initial_required","mean"]),
                         money(paired.loc["collective_liquidation","mean"]),
                         f'{paired.loc["mean_slippage","mean"]*100:+.3f} pp',attack])
    raw_all = pd.concat(all_raw,ignore_index=True)
    raw_all.to_csv(ROOT/"results/combined_pilot_runs.csv",index=False)
    raw_long = pd.concat([pd.read_csv(long/f"baseline_{basis}_runs.csv") for basis in manifests[1]["bases"]],ignore_index=True)
    n_runs = len(raw_all)+len(raw_long)
    n_events = int(raw_all.events.sum()+raw_long.events.sum())
    max_raw = max(raw_all.reserve_shortfall_raw.max(),raw_long.reserve_shortfall_raw.max())
    material = max(raw_all.material_reserve_shortfall.max(),raw_long.material_reserve_shortfall.max())
    attacks = pd.read_csv(pilot/"attack_grid.csv")
    banks = pd.read_csv(pilot/"bank_run_orders.csv")
    scale = pd.read_csv(pilot/"scaling.csv")
    scale_runs = pd.read_csv(pilot/"scaling_simulations.csv")
    grow = pd.read_csv(pilot/"growth.csv")
    spill = pd.read_csv(pilot/"controlled_spillover.csv")
    front_runs = pd.read_csv(pilot/"frontrun_equal_supplies_runs.csv")
    front = front_runs[front_runs.model=="shared"]
    front_summary = pd.read_csv(pilot/"frontrun_equal_supplies_summary.csv")
    attack_stats = front_summary[(front_summary.model=="shared")&(front_summary.metric=="attacker_profit")].iloc[0]
    run_prob = front_summary[(front_summary.model=="shared")&(front_summary.metric=="probability_profitable_attack_run")].iloc[0]
    attack_table = md_table(["Quantity / constraint","Victim fills","Aggregate net profit"],[
        ["a=1,000, b=500, λ=.25, no fees, one attacker", "yes", money(frontrun()["net_profit"])],
        ["Same, 0.3% trading fee", "yes", money(frontrun(fee=".003")["net_profit"])],
        ["Same fee, 2% victim payment cap", "no", money(frontrun(fee=".003",slippage=".02")["net_profit"])],
        ["Same fee, victim executes first", "yes", money(frontrun(fee=".003",ordering="victim_first")["net_profit"])],
        ["Same fee, $1 network cost per attacker transaction", "yes", money(frontrun(fee=".003",gas_per_tx="1")["net_profit"])],
    ])
    extra_bundles = pd.DataFrame([bundle((1,1,1,1),order,lam,fee,victim)
                                  for order in ("forward","reverse") for lam in ("0",".25","1")
                                  for fee in ("0",".003") for victim in (0,1000)])
    extra_bundles.to_csv(ROOT/"results/cross_token_bundle_checks.csv",index=False)
    group = banks[banks.coupling==.25]
    scale_table = md_table(["Tokens","λ=0 backing","λ=.25 backing","λ=.25 new-token price"],[
        [n,money(scale[(scale.tokens==n)&(scale.coupling==0)].initial_reserve.iloc[0]),
         money(scale[(scale.tokens==n)&(scale.coupling==.25)].initial_reserve.iloc[0]),
         money(scale[(scale.tokens==n)&(scale.coupling==.25)].new_token_starting_price.iloc[0])] for n in (2,10,100,1000)])
    growth_table = md_table(["Own-price multiple","Independent capital","Shared λ=.25 capital"],[
        [f"{m}×",money(grow[(grow.tokens==10)&(grow.coupling==0)&(grow.source=="own")&(grow.price_multiple==m)].external_capital.iloc[0]),
         money(grow[(grow.tokens==10)&(grow.coupling==.25)&(grow.source=="own")&(grow.price_multiple==m)].external_capital.iloc[0])] for m in (2,10,100)])
    long_rows = []
    for basis in manifests[1]["bases"]:
        summ = pd.read_csv(long/f"baseline_{basis}_summary.csv")
        for metric in ("collective_liquidation","mean_slippage","trader_realized_pnl"):
            x = summ[(summ.model=="shared_minus_independent")&(summ.metric==metric)].iloc[0]
            multiplier = 100 if metric=="mean_slippage" else 1
            unit = " pp" if metric=="mean_slippage" else " USDC"
            long_rows.append([basis.replace("equal_",""),metric,
                              f'{x["mean"]*multiplier:,.4f}{unit}',
                              f'[{x.mean_ci95_low*multiplier:,.4f}, {x.mean_ci95_high*multiplier:,.4f}]'])
    text = f'''# Research findings: shared quadratic bonding surface

Generated from completed local runs on 28 October 2026. All behavioral outcomes
are **synthetic**, not historical market evidence. The precise equations in
[MATHEMATICS.md](MATHEMATICS.md) define the mechanism being evaluated.

## Assessment

For this model, positive coupling does **not improve fixed-quantity own-token
depth**: the absolute marginal price slope remains k. It raises prices and
required backing when other supplies are positive, adds deterministic contagion,
and enables cross-token transaction-order transfers. Full funding preserves
reserve solvency, but does not make those transfers fair or price discovery useful.
The runs below do not establish a welfare or liquidity advantage over independent
quadratic curves. This is a negative result for that proposed justification;
organic demand, user preferences and alternative mechanisms remain untested.

## What actually ran

- **44 tests passed** in the full implementation suite (55.68 seconds). This
  includes 100-example deterministic Hypothesis properties, randomized valid
  transaction sequences, 1,000-trade Float64/Decimal parity at each of six coupling
  values, accounting identities, constraints, attack formulas and Streamlit app
  interactions. A further targeted app check followed replay refinements.
- Pilot: **100 seeds × 2,000 demand events × six scenarios × two comparison
  bases × two models** = {len(raw_all):,} market runs and {int(raw_all.events.sum()):,} demand events.
- Longer baseline: **100 seeds × 10,000 events × two bases × two models** =
  {len(raw_long):,} market runs and {int(raw_long.events.sum()):,} demand events.
- Combined Monte Carlo: **{n_runs:,} runs, {n_events:,} demand events**. Seeds are
  42–141. Rejected/skipped intentions are counted; they are not fabricated fills.
- Exact analyses: {len(attacks):,} fee/coupling/payment-cap/competition attack cases;
  {banks.seed.nunique()*banks.coupling.nunique():,} complete bank runs with {len(banks):,} recorded redemptions;
  coordinated-wallet acquisition/exit permutations; controlled popular-token and
  crash transitions; 2×/10×/100× capital calculations.
- Scaling: {len(scale_runs):,} actually executed 1,000-event markets across 2, 10,
  100 and 1,000 tokens; three coupling settings and three seeds per setting.
  These scaling runs supplement the Monte Carlo event count above.
- No completed batch used 1,000 seeds, and the non-baseline scenarios were not
  run at 10,000 events per seed. Those larger jobs are supported by the CLI.

Pilot elapsed: {manifests[0]["elapsed_seconds"]:,.1f} seconds; longer baseline:
{manifests[1]["elapsed_seconds"]:,.1f} seconds. The jobs ran concurrently, so elapsed
times reflect local contention and are not independent performance benchmarks.
Both manifests have `status=complete` and source SHA-256 hashes verified against
the current engine. Interrupted development batches are preserved under ignored
`results/scratch`; they are excluded here.

Default assumptions: 10 tokens; p0=.01; k=.0001; shared λ=.25 versus λ=0;
1,000 units per token before capital matching; 100 traders with $1,000 additional
trading cash each; retail 60%, whale 10%, other roles cycled; mean base trade
notional $20 with log-size volatility .8; buy pressure .55; fee 0.3%. The pending
order scenario gives each attacker $500 and a 2% victim payment tolerance. No
network cost applies to Monte Carlo; exact attacks can include an explicit cost.

## Experiment A: independent versus shared

**Proof.** At equal supplies, 10 tokens with 1,000 units each require $600
independent backing and $1,725 shared backing. The initial marginal price rises
from $.11 to $.335. Buying another 100 units costs $11.50 versus $34.00 gross.
The absolute marginal price increase is $.01 in both. Equal initial capital is a
separate comparison: the independent system must begin with more token units.

**Simulated findings.** The table reports paired mean *shared minus independent*
outcomes. Capital is genesis required backing, redemption is the completed-run
collective net redemption, and slippage is average gross execution deviation from
the pre-trade quote. Attacker profit is the shared pending-order scenario's mean,
not a paired difference. Fractions labeled pp are percentage points.

{md_table(["Scenario","Matched basis","Δ initial backing","Δ final net redemption","Δ mean slippage","Attacker mean"],rows)}

Longer baseline paired differences, with approximate 95% seed-mean intervals:

{md_table(["Basis","Metric","Mean difference","95% interval"],long_rows)}

These policies adapt to prices and wallet constraints: matching shocks does not
force identical filled quantities. Greater final reserves can reflect greater
capital paid in, rather than better liquidity. Realized P&L alone excludes
remaining inventory; marked P&L and first-exit values are exported separately.
Gross volume per initial backing is reported as an activity ratio, not established
capital efficiency. No utility function or organic adoption benefit was measured.

## Experiments B and C: popularity and crash contagion

**Exact controlled result.** In the 10-token state above, a 10,000-unit purchase
of Token 0 raises each untouched token by $.25 at λ=.25. Their own demand is zero,
so 100% of that price change is mechanical spillover. Redeeming all 11,000 units
of Token 0 then lowers each other price by $.275, including removal of its
original 1,000 units. These changes are zero at λ=0. The reserve remains backed.

The stochastic popular/crash results are in the paired table and CSVs; their
mixed policies need not create the same magnitude as this controlled example.
Exported price attribution uses the exact identity `Δp_i=kΔq_i+kλΣ(other Δq)`.
Successful issuance can fund early exits in unrelated holdings. Calling it a
subsidy requires the entry/exit sequence: there is no unconditional value creation.

## Experiment D: coordinated launches

**Exact finding.** Coordinated acquisition and complete exit with no intervening
victim trade produces zero aggregate gross profit for every tested acquisition
and exit order; positive fees make it a loss. Wallet splitting does not defeat the
reserve potential. With an intervening purchase, coordinated wallets can capture
order-dependent transfers. Four wallets buying a total of 1,000 B units before
a victim buys 1,000 A units earn $25 gross at λ=.25, or $24.565 after 0.3% fees,
when fully funded and allowed that order. See `cross_token_bundle_checks.csv`.

Same-token early positioning also profits from subsequent buyers at λ=0, so
same-token bundle profits are not evidence of a new shared-reserve flaw.
Mixed-token sequences in `bundle_grid.csv` separate aggregate cost from the
distribution across coordinated wallets. No creator receives unbacked issuance.

## Experiment E: cross-token frontrunning

**Proof and numerical verification.** With one attacker, fixed quantities and a
filled victim, `gross profit=kλab`. This exactly equals the victim's extra gross
purchase cost. Fee-adjusted profit is `(1-f)kλab-2fC-network_cost`, where C is the
attacker's gross acquisition cost. This is value extraction from ordering, while
the reserve stays solvent. It is not a closed-loop collateral-draining arbitrage.

Standard exact workbench cases (p0=.01, k=.0001, initial A=B=1,000):

{attack_table}

The 2% cap rejects this large victim order after the attack; the attacker still
pays round-trip trading fees. Competitors are separately funded wallets and the
exit order is explicit. Their aggregate and individual profits are available in
the workbench. Network charges are explicitly capital constrained and transferred
to a modeled network account, with no assumed gas market or private ordering.

**Synthetic distribution**, equal initial supplies, λ=.25, 0.3% fee, 2% cap:
mean attacker total realized profit {money(attack_stats["mean"])} per 2,000-event run;
median {money(attack_stats["median"])}; standard deviation {money(attack_stats["std"])};
5th/95th percentiles {money(attack_stats["q05"])}/{money(attack_stats["q95"])};
worst observed {money(attack_stats["min"])}; mean 95% interval
[{money(attack_stats.mean_ci95_low)}, {money(attack_stats.mean_ci95_high)}].
Profitable-run frequency {run_prob["mean"]:.1%}, with Wilson 95% interval
[{run_prob.mean_ci95_low:.1%}, {run_prob.mean_ci95_high:.1%}]. Mean within-run
profitable-opportunity fraction {front.attack_success_frequency.mean():.1%}.
These are different denominators; neither estimates a real-world attack rate.
Attack sizing/order is a synthetic heuristic, not an optimal adversary.

## Experiment F: scaling

Uniform supply 1,000 units per existing token; p0=.01, k=.0001:

{scale_table}

**Proof.** With fixed per-token units and positive λ, backing grows quadratically
with token count and existing/new token price intercepts grow linearly. A token
can start expensive before receiving any demand. Denomination comparability is a
major modeling assumption: this surface is not invariant to arbitrary token
decimal/unit changes. At λ=1 all token marginal prices coincide regardless of
which name attracted demand.

**Executed scale runs.** All {len(scale_runs)} completed scaling simulations stayed
within the declared reserve tolerance. Their max material shortfall was
{scale_runs.material_reserve_shortfall.max():.8g} USDC. Timing distributions are saved
in `scaling_simulations.csv`; median 1,000-token run time was
{scale_runs[scale_runs.tokens==1000].elapsed_seconds.median():.4f} seconds for 1,000
events. This demonstrates local computability at those settings, not economic
safety, production capacity, or a large trader-population benchmark. Engine
quotes/trades are O(1); full snapshots, scans and storage are not.

## Experiment G: bank runs, solvency and fairness

**Proof and exact execution.** Fully funded issuance and reserve-difference
redemption telescope: all holders can redeem, and aggregate gross receipts equal
R regardless of exit order. The exact full-redemption tests left zero required
reserve. Fees and donated buffers are separately accounted for.

At λ=.25 with ten 1,000-unit positions, first exit receives
{money(group[group.exit_position==0].proceeds.mean())}; last exit receives
{money(group[group.exit_position==9].proceeds.mean())}, even though quantities match.
At λ=0 each receives $60. Entry costs also depend on order, so gross receipts are
not themselves P&L; the bank-run export includes cost-aware realized P&L.
Total system solvency therefore coexists with meaningful order risk and contagion.

Across the Monte Carlo batches, largest raw floating backing discrepancy was
{max_raw:.8g} USDC and largest material shortfall was {material:.8g} USDC. The fast
engine tolerance is `1e-9 * max(1, initial external capital, current reserve)`;
no such tolerance is used by the Decimal accounting tests. Floating evidence is
not a substitute for the mathematical solvency proof or settlement-rounding tests.

## Experiment H: price runs and paper capitalization

Fixed initial 10-token supplies; no fees; only the target token receives new
issuance. Gross new capital needed for the indicated marginal-price multiple:

{growth_table}

**Proof.** Capital equals `p²(m²-1)/(2k)` for an own-token run. Coupling's higher
starting intercept makes the same relative move more expensive at the matched
supply state. Cross-token issuance can raise a target's price without target
buying, but the other buyers must still fund their reserve differences. The growth
CSV reports that route separately. No calibrated adoption model supports a claim
that coupling makes large organic price runs more likely.

Collective paper market cap satisfies `M=2R-p0Q`, hence lies between R and 2R
for positive supplies. Complete gross liquidation is R, not M. Per-token or
per-wallet first-exit quotes cannot be added into jointly executable proceeds.

## Answers to the ten design questions

1. **Better liquidity?** No fixed-quantity depth improvement follows from this
   surface; own slope is unchanged. Simulated relative slippage cannot establish it.
2. **More capital to buy?** Yes at matched supplies with other positive supplies;
   initial backing also rises. Equal-capital results must change initial issuance.
3. **Unrelated appreciation?** Exactly `kλΣΔq_other`; the controlled example had
   entirely unrelated appreciation. Real demand attribution remains untested.
4. **Indirect manipulation?** Yes, funded issuance elsewhere deterministically
   moves a token's quote; it costs actual capital and unwind changes the quote again.
5. **Cross-token ordering profits?** Yes under funded, fee/slippage-feasible
   sequences, as the exact formula and workbench verify.
6. **Subsidies?** Cross terms can transfer value from later successful issuance
   to earlier unrelated holdings, conditional on entry and exit ordering.
7. **Fragility?** Mechanical price contagion and exit-order risk increase with λ.
   Endogenous real-world run probability is not established by these policies.
8. **Thousands of tokens?** Computable and solvent under valid accounting in
   tested runs; economically costly at fixed units, with elevated new-token prices.
9. **Larger runs easier?** Not for matched-supply own-token relative moves in this
   model. Spillover paper runs require external issuance capital elsewhere.
10. **Useful shared reserve?** Shared custody alone changes no λ=0 execution
   economics. Positive coupling redistributes exposure; no measured net welfare
   benefit here compensates for that added exposure and ordering risk.

## Proposed mitigations — not implemented or validated as replacements

- Cap coupling or use fixed-capacity isolated cohorts to limit total exposure.
  Repricing λ when membership changes requires explicit collateral and ownership
  accounting; it must not be silently normalized during trading.
- Investigate batch clearing or protected transaction submission against the
  specified ordering attack. Their effectiveness and decentralization assumptions
  need separate models; this simulator does not establish them.
- Study a different convex potential, e.g. separable own-token terms plus a global
  term with bounded marginal derivative. Re-derive funding, derivatives, attack
  profits and scaling from that potential before claiming an improvement.
- Retain λ=0 with shared custody as a control. Operational simplicity or shared
  infrastructure might be useful, but those benefits were not measured here.

## Limits, evidence and reproduction

No real market data, external exchange/arbitrage, gas auction, latency network,
strategic equilibrium, borrower, short seller, organic narrative model, protocol
governance, denomination policy or six-decimal cash rounding is included. Roles
are transparent assumed heuristics. Genesis inventory is paid for by attributed
holder contributions in addition to their trading cash; extra reserve is donated.
Net external flow means trader-to-curve cash including fees, within a closed
simulated economy. Fee recipients and the donation sponsor are distinct from
trader P&L. A minimum marginal price is not a promise that every holder can exit
at the displayed quote.

Seed-mean intervals use the normal approximation across 100 independent seeds;
paired intervals use matched seed differences. They quantify uncertainty inside
this simulator, not model uncertainty or out-of-sample predictive accuracy. The
2,000-event and 10,000-event horizons must not be pooled as one identical design.
Worst observed outcomes are sample extrema, not guaranteed bounds.

Artifacts: `results/pilot/*_runs.csv` and `*_summary.csv`,
`results/long_baseline/*`, `results/cross_token_bundle_checks.csv`, and
`results/research_charts.html`. Manifests include exact versions, configurations,
completion states, source hashes and elapsed time. Reproduce with:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q
.\\.venv\\Scripts\\python.exe -m bonding_lab.cli research --seeds 100 --events 2000 --out results/reproduce_pilot
.\\.venv\\Scripts\\python.exe -m bonding_lab.cli research --seeds 100 --events 10000 --scenarios baseline --out results/reproduce_long
.\\.venv\\Scripts\\python.exe -m streamlit run dashboard.py
```

Run `python scripts/build_report.py` to regenerate this report from its original
completed directories. A failed or interrupted manifest is rejected, and source
hash mismatches stop report generation. See README for install commands and the
supported larger CLI batches.
'''
    (ROOT/"RESEARCH_FINDINGS.md").write_text(text,encoding="utf-8")
    figures = [
        px.box(raw_all[(raw_all.scenario=="baseline")&(raw_all.basis=="equal_supplies")],x="model",y="collective_liquidation",title="Synthetic baseline: final collective net redemption, 100 seeds"),
        px.histogram(front,x="attacker_profit",nbins=25,title="Synthetic pending-order attack profit, 100 seeds"),
        px.line(scale,x="tokens",y="initial_reserve",color="coupling",log_x=True,log_y=True,title="Mathematical reserve scaling, fixed 1,000 units per token"),
        px.box(banks,x="exit_position",y="proceeds",color="coupling",title="Exact full-redemption sequences: gross proceeds by exit position"),
        px.line(spill,x="coupling",y=["spillover","other_crash_drop"],title="Exact controlled cross-token popularity and crash effects")
    ]
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Shared Bonding Lab: executed research</title><body><h1>Executed synthetic research</h1><p>These are simulated outcomes and mathematical calculations, not historical data. Read RESEARCH_FINDINGS.md for assumptions and limits.</p>']
    for i,fig in enumerate(figures):
        parts.append(fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>')
    (ROOT/"results/research_charts.html").write_text("\n".join(parts),encoding="utf-8")
    print(f"Reported {n_runs:,} Monte Carlo runs / {n_events:,} demand events; source hashes verified")


if __name__=="__main__":
    main()
