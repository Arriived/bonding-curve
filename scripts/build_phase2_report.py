"""Report only completed, hash-matched Phase 2 evidence; preserve Phase 1 files."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import plotly.express as px

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.experiments import distribution
from bonding_lab.phase2.surfaces import calibrate,ExactSurface,Asset,F


def money(x):return "n/a" if pd.isna(x) else (f"-${abs(x):,.2f}" if x<0 else f"${x:,.2f}")
def table(headers,rows):
    return "| "+" | ".join(headers)+" |\n| "+" | ".join(["---"]*len(headers))+" |\n"+"\n".join("| "+" | ".join(map(str,row))+" |" for row in rows)


def large_bounded_attack():
    spec,x=calibrate("bounded",10,11000)
    c=ExactSurface(spec,".003")
    for i in range(10):c.admit(Asset(str(i),10**9))
    c.wallet("seed",12000);c.wallet("bot",5000);c.wallet("victim",20000)
    for i in range(10):c.trade("seed",i,str(x),"buy")
    gross,fee=c.quote(0,".6","buy")
    prepayment=gross+fee
    initial=c.cash["bot"]
    c.trade("bot",1,".1","buy")
    newgross,newfee=c.quote(0,".6","buy")
    cap=prepayment*F("1.01")
    c.trade("victim",0,".6","buy",max_payment=cap)
    c.trade("bot",1,".1","sell")
    c.assert_invariants()
    return dict(victim_fraction=.6,attacker_fraction=.1,fee=.003,attacker_capital=5000,victim_capital=20000,
                victim_filled=True,victim_payment_tolerance=.01,victim_original_payment=float(prepayment),
                victim_extra_payment=float(newgross+newfee-prepayment),
                attacker_profit_after_trading_fees=float(c.cash["bot"]-initial),network_expense=0.,
                accounting="exact rational; actual funded mint and burn")


def main():
    out=ROOT/"results/phase2"
    manifest=json.loads((out/"manifest.json").read_text())
    assert manifest["status"]=="complete","Incomplete experiment"
    for file,digest in manifest["source_sha256"].items():
        assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest,"Source changed: "+file
    audit=json.loads((ROOT/"results/phase2_audit/audit.json").read_text())
    assert audit["status"]=="complete"
    raw=pd.read_csv(out/"all_runs.csv");summary=pd.read_csv(out/"summary.csv")
    assert len(raw)==manifest["seeds"]*len(manifest["scenarios"])*4
    assert raw.total_initial_cash.nunique()==1 and raw.sponsor_net_deployed.nunique()==1
    # Independently recompute every summary distribution from the raw seed rows.
    for row in summary.to_dict("records"):
        if row["n"]==0:continue
        subset=raw[raw.scenario==row["scenario"]]
        arch=row["architecture"]
        if arch.endswith("_minus_independent"):
            arch=arch.removesuffix("_minus_independent")
            p=subset.pivot(index="seed",columns="architecture",values=row["metric"])
            values=p[arch]-p["independent"]
        else:values=subset[subset.architecture==arch][row["metric"]]
        for key,value in distribution(values).items():
            assert np.isclose(row[key],value,atol=1e-7,rtol=1e-8),(row["metric"],key)
    tests=ET.parse(ROOT/"results/phase2_validation.xml").getroot()[0]
    assert tests.attrib["failures"]=="0" and tests.attrib["errors"]=="0"
    count=int(tests.attrib["tests"]);testtime=float(tests.attrib["time"])
    zero=pd.read_csv(out/"zero_fee_liquidity.csv")
    fee=pd.read_csv(out/"initial_liquidity.csv")
    joint=pd.read_csv(out/"joint_liquidity.csv").query("ordering=='forward'").set_index("architecture")
    tox=pd.read_csv(out/"toxic_control.csv").set_index("architecture")
    bounded=pd.read_csv(out/"bounded_exact.csv")
    attacks=pd.read_csv(out/"order_attacks.csv")
    scale=pd.read_csv(out/"scaling.csv")
    arb=pd.read_csv(out/"arbitrage_controls.csv")
    matched=pd.read_csv(out/"depth_matched_independent.csv")
    extra=large_bounded_attack()
    (out/"large_bounded_attack.json").write_text(json.dumps(extra,indent=2),encoding="utf-8")
    exits=pd.read_csv(out/"retail_exit_checks.csv")
    assert len(exits)==120 and exits.source_state_reproduced.all()
    exitrows=[]
    for (scenario,arch),group in exits.groupby(["scenario","architecture"]):
        exitrows.append([scenario,arch,money(group.pre_exit_marked_pnl.mean()),money(group.actual_full_exit_pnl.mean())])
    liquidity=[]
    for arch in ("independent","quadratic","bounded","weighted","hub"):
        b=zero[(zero.architecture==arch)&(zero.side=="buy")].iloc[0]
        s=zero[(zero.architecture==arch)&(zero.side=="sell")].iloc[0]
        f=fee[(fee.architecture==arch)&(fee.side=="buy")].iloc[0]
        liquidity.append([arch,money(b.initial_reserve),money(b.executed_cash),money(s.executed_cash),
                          money(b.executable_reference_notional_1pct),money(f.executable_reference_notional_1pct)])
    depthratio=zero.query("architecture=='weighted' and side=='buy'").executable_reference_notional_1pct.iloc[0]/zero.query("architecture=='hub' and side=='buy'").executable_reference_notional_1pct.iloc[0]
    capital=[]
    for arch in ("independent","quadratic","bounded","weighted"):
        r=raw[(raw.architecture==arch)&(raw.seed==42)].iloc[0]
        capital.append([arch,money(r.sponsor_net_deployed),money(r.total_initial_cash),money(r.initial_cash_reserve),
                        money(r.token_inventory_cost),money(r.creator_cash),money(r.initial_genesis_mark_gain)])
    batch=[]
    for scenario in manifest["scenarios"]:
        for arch in ("independent","quadratic","bounded","weighted"):
            group=raw[(raw.scenario==scenario)&(raw.architecture==arch)]
            x=summary[(summary.scenario==scenario)&(summary.architecture==arch)&(summary.metric=="arb_profit")].iloc[0]
            batch.append([scenario,arch,money(x["mean"]),f"[{money(x.mean_ci95_low)}, {money(x.mean_ci95_high)}]",
                          money(group.retail_realized_pnl.mean()),money(group.retail_pnl.mean()),
                          money(group.lp_pnl.mean()),money(group.lp_loss_vs_hodl.mean())])
    paired=[]
    for scenario in manifest["scenarios"]:
        x=summary[(summary.scenario==scenario)&(summary.architecture=="bounded_minus_independent")&(summary.metric=="arb_profit")].iloc[0]
        paired.append([scenario,money(x["mean"]),f"[{money(x.mean_ci95_low)}, {money(x.mean_ci95_high)}]"])
    risk=[]
    for arch in ("weighted","hub"):
        x=tox.loc[arch]
        risk.append([arch,money(x.attack_profit),f"{x.cash_depletion_fraction:.2%}",f"{x.unrelated_price_change:.2%}",
                     money(x.lp_nav),money(x.lp_loss_vs_hodl)])
    joint_rows=[[a,money(joint.loc[a,"summed_initial_buy_quotes"]),money(joint.loc[a,"actual_joint_buy_cost"])] for a in ("independent","quadratic","bounded","weighted","hub")]
    attackrows=[]
    for arch in ("independent","quadratic","bounded","weighted"):
        for f in (0,.003):
            x=attacks[(attacks.architecture==arch)&(attacks.fee==f)&(attacks.victim_fraction==.01)].iloc[0]
            attackrows.append([arch,f"{f:.1%}",money(x.attacker_net_profit),money(x.victim_extra_payment)])
    fixed_scaling=[[int(x.tokens),f"{x.global_premium:,.4f}",money(x.bounded_required),money(x.quadratic_required)] for x in bounded.itertuples()]
    lp=raw[raw.architecture=="weighted"]
    worst=lp.loc[lp.lp_pnl.idxmin()]
    scale_rows=[]
    for n in (2,10,100,1000):
        group=scale[scale.tokens==n]
        scale_rows.append([n,int(len(group)),f"{group.elapsed_seconds.max():.4f}",f"{group.max_cash_conservation_error.max():.3g}"])
    max_cash=max(raw.max_cash_conservation_error.max(),scale.max_cash_conservation_error.max())
    max_back=max(raw.backing_absolute_error.max(),scale.backing_absolute_error.max())
    min_shortfall=raw.backing_shortfall.max()
    social=[]
    for share in (.2,.3,.5):
        social.append([f"{share:.0%}",money(10000*share),money(tox.loc["weighted","lp_nav"]*share),money(tox.loc["weighted","lp_pnl"]*share)])
    text=f'''# Phase 2 findings and research verdict

29 October 2026. **All market data in this study are synthetic.** The mechanics
are mathematical models; the measured distributions do not predict real memecoin
returns, demand, attack rates or safe admission decisions.

## Verdict

**No tested design establishes a robust liquidity improvement without a material
tradeoff in exposure or assumptions.** The bounded potential fixes the original
unbounded global premium and quadratic fixed-supply scaling, but does not create
free depth or remove ordering transfers. An inventory AMM genuinely reuses cash
across tokens and improves *one-token local depth* over equally funded isolated
pools. It also socializes toxic-token losses across the common reserve. The
unvetted memecoin admission case does not support calling that tradeoff safe.

An isolated USDC hub/cohort is the conservative control for further work: it can
share custody, routing and software while enforcing cash-risk boundaries. That
is infrastructure sharing, not a claim of pooled financial liquidity gains.
No production protocol or token admission recommendation follows from this study.

## Completed work and validation

- Original audit verified **{audit['historical_runs_verified']:,} old runs /
  {audit['historical_events_verified']:,} demand events**, both manifests and source
  hashes, all stored distribution summaries, matched funding and 84 selected-seed
  re-executions. See [PHASE1_AUDIT.md](PHASE1_AUDIT.md).
- **{count} tests passed** in {testtime:.2f} seconds, including the unchanged
  dashboard tests, exact rational invariant/property tests, raw redenomination,
  calibration, finite wallets/dealer depth, convexity, attack identities, and
  Decimal/float AMM checks. Test evidence: `results/phase2_validation.xml`.
- Main batch: **{manifest['seeds']} matched seeds × {manifest['config']['events']}
  demand events × five scenarios × four architectures = {len(raw):,} market runs
  and {int(raw.events.sum()):,} demand events**. Seeds 42–91; elapsed
  {manifest['elapsed_seconds']:.2f} seconds. There are no claimed 1,000-seed results.
- Additional controls: exact redemption, bounded-premium scaling, finite-size
  pending-order attacks, joint execution, an independently depth-matched curve,
  external-price divergence without retail flow, a finite toxic-inventory sale,
  and {len(scale)} executed scaling markets at 2/10/100/1,000 tokens.
- A further check reproduced 60 saved terminal market states (three selected
  seeds in every scenario/architecture) and executed 120 retail portfolio exits
  in forward/reverse order. These are replay validations, not additional
  independent Monte Carlo samples.
- All Phase 2 source hashes and seed distribution summaries were independently
  verified again before writing this report. The manifest is complete. A separate
  small development smoke batch is not pooled into these findings.

## 1. Audit: what survives and what needs qualification

At fixed original coefficients, own slope remains k and cross slope is kλ.
Funded reserve differences telescope, market cap is `2R-p0Q`, and the no-fee
ordering transfer is `kλab`. These are proven conditional properties. The old
equal-capital runs fairly matched backing plus trading cash, but began at different
prices. Their lower relative slippage was not proof of improved depth. For example,
equal-backed initial prices were .335 shared and .186011 independent; both moved
by .01 for a 100-unit trade. Relative slippage divides by those different prices.

One defect was repaired: the old fast constructor accepted underfunding within
1e-9, including a $145 obligation funded with $144.9999999995. It now rejects
strictly lower genesis funding. None of the old default runs used that branch;
they automatically funded the computed requirement. The original source is
preserved for provenance, and the old findings are not silently rewritten.

## 2. Bounded coupling: mathematical result

Use fractions `x_i=q_i/S_i` of each verified immutable authorized supply, with
fixed cohort admission and no arbitrary raw-unit sums:

```
R = sum(a_i x_i+b_i x_i²/2) + gamma X²/(tau+X), X=sum x_i
P_i = a_i+b_i x_i+gamma[1-tau²/(tau+X)²]
raw price = P_i/S_i
H_ij = 2 gamma tau²/(tau+X)³ (i != j)
H_ii = b_i+H_ij
```

The Hessian is positive definite for positive b_i; prices are positive. Global
influence is less than gamma even with many assets. Changing raw denomination
with S leaves every cashflow invariant; exact property tests verify it. This does
not solve Sybil identity or false supply-attestation problems. Only screened,
fixed-capacity cohorts are admitted, at zero newly issued supply, without changing
old coefficients. There is no claim of safe permissionless admission.

Funded mint/burn uses exact potential differences. The rational reference enforces
cash, ownership and reserve equalities exactly. Full redemption returned all
required gross backing. At fixed parameters and .1 issued fraction per token:

{table(['Tokens','Global premium per full claim (cap 2,000)','Bounded backing','Quadratic backing'],fixed_scaling)}

The bounded fixed-state reserve scales linearly with n, while the original
quadratic cross term scales as n². **This is an improvement in exposure bounds
and scaling, not evidence of extra executable liquidity.** All parameters stay
fixed within each run. Raw prices inherit the cap divided by S_i.

## 3. Budget fairness and instrument differences

Every sponsor deploys a net $10,000. Every world begins with $136,000 total USDC,
including identical dealer, retail and arbitrage funding. Dealer inventory costs
$1,000 and is paid, and an AMM's $5,000 seed token inventory is also paid. All
starting token/reference prices equal $10,000 **per whole authorized-supply claim**;
this is not one raw memecoin's price. See the full flow derivation in
[PHASE2_DESIGN.md](PHASE2_DESIGN.md).

| Architecture | Sponsor net deployment | World initial USDC | Initial mechanism cash | Paid pool inventory | Creator cash after seeding | Initial genesis mark/cost gain |
| --- | --- | --- | --- | --- | --- | --- |
'''+"\n".join("| "+" | ".join(row)+" |" for row in capital)+f'''

The extra $1,000 curve collateral is funded by the dealer's secondary purchase,
not hidden free capital. In an AMM, paid token purchases go to the creator instead.
Those flows conserve the same global starting USDC. The AMM creator's remaining
authorized stock is finite; its undeployed FDV is not treated as LP funding.

The instruments differ: a surface issues funded redemption claims; an AMM trades
existing tokens and LPs hold a residual portfolio. We therefore report curve
operator fee income, sponsor mark changes and AMM LP NAV separately. Collateral
offset by redemption liabilities is never called LP profit. Initial genesis
mark/cost gains are excluded from subsequent sponsor mark changes. Identical
deployed cash budgets do not imply identical claims, genesis asset amounts or
total marked value of undeployed creator inventory. These are comparison limits,
not reasons to ignore the real inventory expense.

## 4. Executable liquidity at aligned starts

Zero-fee controls isolate curve/pool geometry. A $100 reference-notional trade is
.01 of an authorized supply. Sell quotes require owned eligible tokens; the
engine does not permit selling arbitrary unissued creator tokens into a surface.
The last columns show token reference notional within a 1% all-in execution
deviation at the aligned initial price, with zero and 0.3% fees respectively.

{table(['Architecture','Initial cash','Buy $100 token notional: cash paid','Sell $100 notional: cash received','1% buy depth, no fee','1% buy depth, fee'],liquidity)}

The original quadratic has been recalibrated here: b is reduced from
43,636.36 independent to 13,426.57 quadratic to align prices and budgets. The
old statement `H_ii=k` still holds. We must not mislabel this coefficient change
as the effect of sharing reserves at fixed k.

**Falsification control:** a fully independent curve with floor coefficient
{matched.a.iloc[1]:,.4f}, b={matched.b.iloc[1]:,.4f}, the same $11,000 backing and
same initial $10,000 price executes the $100 buy for
{money(matched.exact_buy_100_reference_notional.iloc[1])}, matching the recalibrated
quadratic exactly. Its seed quantity differs and is reported. Coupling is not
necessary for this local depth. Parameters and seed distribution are economic
choices; this single counterexample is not a universal optimal curve either.

The bounded curve's modest depth gain over the fixed-floor independent baseline
is similarly calibration-dependent. It does not establish a unique shared-cash
liquidity advantage. No paper cap or rising quote is used as a depth measure.

## 5. Genuine shared AMM: benefit and joint-capacity test

The weighted pool has actual USDC plus paid token inventories. It uses a
constant-mean invariant with half the weight on USDC and equal remaining weights.
A separate hub control holds the **same total cash and token inventory**, with
each token's USDC allocation ring-fenced in a 50/50 pool. See the
[weighted invariant source](https://docs.balancer.fi/whitepaper.pdf) and
[swap definitions](https://docs-v2.balancer.fi/reference/math/weighted-math.html).

At n=10, the weighted pool supplies **{depthratio:.3f}×** the hub's zero-fee local
1%-cost buy depth. The initial differential slope ratio is `(n+1)/(2n)=.55`,
approaching a 2× depth gain for many tokens. It is not n copies of the cash pool.
This is a measurable genuine cash-sharing effect under the matched inventory
weights, unlike price spillover on a minting surface.

For a .01-fraction buy in **each** of the ten tokens, the initial one-token quotes
are incompatible simultaneous states. Sequential exact executions give:

{table(['Architecture','Sum of initial individual quotes','Actual joint buy cost'],joint_rows)}

The weighted and hub pools both require $1,250 for this symmetric joint demand.
The one-token benefit disappears for that balanced portfolio trade. Inventory
depletion and price changes prevent every token from treating the cash as its
own untouched liquidity reserve.

## 6. Toxic admission and socialized LP risk

A fixed pool rejects attaching a new token to existing cash and changing weights
mid-run. Known bad admission prices/unverified supply are also rejected by the
declared screening check. The stress scenario represents weak screening/future
failure: a previously admitted token's external value collapses by 99.99%.

A bot **pays $0.94** for .94 of the authorized issue from the creator at that
collapsed reference price, then sells the real finite stock to the AMM. This
explicit private OTC leg is not constrained by the public dealer's displayed
depth, but is constrained by creator inventory and bot capital. It is not a free
mint into a curve. The surface admits no such creator redemption right.

{table(['AMM','Attacker cash profit after fee/gas','Common cash depleted','Healthy-token quote change','LP final NAV','LP loss vs holding after collapse'],risk)}

The shared pool's loss goes beyond the toxic asset's isolated cash allocation.
Selling that asset lowers the common cash and all other token quotes. The hub
loss is confined to the toxic subpool; healthy quotes are unchanged. Pool balances
stay positive in both: **cash positivity does not mean LP capital was preserved**.
No fixed-dollar LP deposit guarantee exists in this model. Losses are borne by
pro-rata LP shares; for illustrative 20%/30%/50% owners of this shared pool:

{table(['LP share','Original capital','Post-stress NAV share','Total marked loss'],social)}

This share table is a pro-rata accounting allocation of the executed pool NAV,
not another stochastic LP simulation. No insurance or replenishment is assumed.
It does not model LP withdrawals during the attack. Cash cannot be safely exposed
to arbitrary low-quality assets merely by choosing a common invariant.

## 7. External markets, extraction and trader/LP outcomes

Each token gets independent lognormal reference innovations with per-event
volatility .02; the divergence scenario additionally doubles one token and halves
another, the crash reduces one by 99%, and the joint run halves every reference
mid. All models receive the same shocks and retail intentions. These are chosen
stress assumptions, not empirically fitted return distributions.
Each world has a sponsor, one finite dealer, an aggregate retail wallet, an atomic
arbitrage wallet, a creator and a network-expense account.

The outside dealer has finite cash and paid token inventory. A window's linear
quote curve has finite depth and spread; order flow moves its quote, and inventory
never resets. Two-leg arbitrage must fund both legs, obey ownership/capacity, and
cover a $.01 route expense after fees. Up to two optimized candidate routes are
executed per event. This is a limited, atomic arbitrage policy rather than an
optimal latency-aware adversary or an equilibrium solver.

The following are seed means. Intervals are approximate 95% intervals for the
mean arb cash gain across 50 seeds. AMM LP metrics are intentionally N/A for
surfaces. Every gain here is realized bot cash; reference marking is used for
inventory holders and LP NAV, not to manufacture bot profits.

{table(['Scenario','Architecture','Arb cash gain','95% mean interval','Retail realized P&L','Retail marked P&L','AMM LP marked P&L','AMM LP vs HODL'],batch)}

Matched-seed **bounded minus independent** arb-profit differences:

{table(['Scenario','Mean difference','95% paired interval'],paired)}

Bounding influence reduces the quadratic surface's exposure in these settings,
but does not make independent assets track unrelated markets. In the no-retail
2×-one-token reference control, realized bot gains were
{money(arb[(arb.architecture=='independent')&(arb.shock_factor==2)].arb_profit.iloc[0])}
independent,
{money(arb[(arb.architecture=='quadratic')&(arb.shock_factor==2)].arb_profit.iloc[0])}
quadratic,
{money(arb[(arb.architecture=='bounded')&(arb.shock_factor==2)].arb_profit.iloc[0])}
bounded and
{money(arb[(arb.architecture=='weighted')&(arb.shock_factor==2)].arb_profit.iloc[0])}
weighted. Finite available claims/depth constrain the opposite-direction route.
Both direction controls and dealer P&L are exported, so extraction is not
automatically attributed to LPs or backing insolvency.

**Important validity limit:** a frictionless market cannot persistently sell
immediately redeemable funded claims below their available redemption value.
Here an exogenous finite dealer can post such a quote and lose stock/cash.
Large residual quote/reference gaps can remain after its inventory is exhausted.
They are not automatically executable arbitrage opportunities. This limits any
economic ranking based on this synthetic reference process, especially crash
cases with puttable claims. It does not invalidate the recorded funded trades or
the cross-derivative/ordering proofs.

**Executed closing control:** reference marks are not assumed to equal available
redemption cash. The following diagnostic replays seeds 42, 77 and 91, verifies
their terminal cash/reserve/P&L against the stored main runs, then actually sells
the retail portfolio through the mechanism. Values are means of those three
selected states and both exit orders, **not** new population estimates:

{table(['Scenario','Architecture','Pre-exit reference-marked P&L','Actual closing cash P&L'],exitrows)}

This exposes both effects: funded claims may redeem above a distressed outside
mark; AMM inventory can execute below a favorable paper mark because of price
impact. No simultaneous other holder exits are assumed. The largest remaining
float cap-boundary dust was {exits.remaining_token_fraction.max():.4g} of one
authorized supply. The exit caller respected strict input caps, recorded the
remainder and did not erase it; exact rational surface tests have no such dust.
Raw exit cases are in `retail_exit_checks.csv`.

Worst observed AMM LP marked outcome in this batch was {money(worst.lp_pnl)}
(scenario `{worst.scenario}`, seed {int(worst.seed)}). This is a sample extreme,
not a worst-case bound. Fee tokens valued at an internal quote can look valuable
while being toxic externally; the exported `fee_value_at_execution` is only that
internal-mark inventory diagnostic. LP profitability above uses outside-valued
NAV, not paper fee income.

## 8. Ordering attacks remain after bounding

The bounded exact gross transfer, with t=tau+X, is:

```
gamma tau² a b (2t+a+b) / [t(t+a)(t+b)(t+a+b)]
```

It is positive when gamma,a,b are positive. Net profit subtracts proportional
trading fees and network costs; tighter victim payment limits can reject some
sequences. For a=.01, b=.01 in the aligned initial state:

{table(['Architecture','Fee','Attacker net cash gain','Victim extra payment'],attackrows)}

Small sampled bounded orders lose after the fee; that is not a security proof.
An additional **exact rational funded execution** with a=.6, b=.1, attacker
capital $5,000 and victim capital $20,000 earned
{extra['attacker_profit_after_trading_fees']:.6f} USDC after 0.3% fees, before
network expense. Its victim's extra payment was
{extra['victim_extra_payment']:.6f} USDC on an initial quote of
{money(extra['victim_original_payment'])}; the victim still filled with a **1%**
maximum-payment tolerance. All issuance fractions stayed below 1. Details and
exact-accounting scope are saved in `large_bounded_attack.json`. Bounding limits
the attack's magnitude; it does not eliminate the transfer or guarantee fees do.

## 9. Solvency, conservation and scale

Exact rational surface tests proved equality of required/actual backing on tested
funded paths and complete redemption. The proof is inductive potential-difference
accounting, conditional on the admitted token rules. Float dynamic runs showed
max cash-conservation error {max_cash:.4g} USDC and max backing absolute error
{max_back:.4g} USDC. Raw positive surface shortfalls were at most
{min_shortfall:.4g} USDC. All were within the declared research tolerances; none
is evidence of intentional underfunding being allowed. AMM solvency means honoring
pro-rata inventory ownership, not a fictitious full-dollar guarantee.

Fixed **total** capital scaling tests (100 events each, all four plus the hub):

{table(['Tokens','Executed worlds','Largest per-world elapsed seconds','Max cash error USDC'],scale_rows)}

At fixed total capital, per-asset inventory/depth must shrink as more independent
assets share it. O(1) local surface/pool quote formulas do not remove that economic
constraint. Reports and bot candidate scans are O(n), not O(1); holdings storage
is O(number of wallets × n). These timings test local research computation,
not deployment throughput or robust large-cohort economics.

## 10. What is and is not demonstrated

| Design | Demonstrated property | Unresolved or adverse consequence |
| --- | --- | --- |
| Independent curves | Funded issuance/redemption; no mechanical cross-token quote effects | Parameters/price floors drive depth; external option-value/reference process needs care |
| Original quadratic | Lower local slope is possible after explicit recalibration | Same local depth is reproducible without coupling; external divergence/order transfers and unbounded fixed-shape scaling |
| Bounded surface | Unit invariance, capped global premium, convexity, linear fixed-shape reserve scaling | Coupling transfers remain; no unique liquidity advantage established; screened admission assumptions |
| Shared weighted AMM | Real, paid-inventory local depth gain versus isolated hub at matched seed value | Finite/joint capacity, toxic reserve depletion, LP inventory risk and healthy-token contagion |

None establishes a permissionless, risk-free reserve-sharing advantage. A pooled
AMM may be worth studying for a **pre-screened, exposure-capped asset cohort**
whose LPs explicitly accept inventory risk. Whether its fees compensate that risk
requires calibrated demand, asset-quality assumptions, admission costs and a stated
risk budget; these simulations do not answer it. For independently launched
unvetted memecoins, the present evidence favors retaining financial isolation as
the safety baseline while sharing operational infrastructure.

The bounded potential is useful as an exposure-limited control, not a reason to
force price coupling. No design is defended simply because it was implemented.

## Reproduction and limitations

See [PHASE2_README.md](PHASE2_README.md) for full commands and the data dictionary:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q
.\\.venv\\Scripts\\python.exe scripts/audit_phase1.py
.\\.venv\\Scripts\\python.exe -m bonding_lab.phase2 --seeds 50 --events 300 --out results/phase2_reproduction
.\\.venv\\Scripts\\python.exe scripts/verify_phase2_exits.py
.\\.venv\\Scripts\\python.exe scripts/build_phase2_report.py
```

The existing Streamlit dashboard was not rebuilt. The new standalone interactive
figures are `results/phase2/research_charts.html`. CSVs and a complete manifest
record the parameters, paid budgets, seeds, hashes and actual outcomes. Exact
extra-attack and report validation metadata are saved next to them.

No real exchanges, contracts, oracle security, transfer-tax/rebase tokens,
borrowing, gas auctions, delayed settlement, token admission attestations, dynamic
weight changes, strategic LP withdrawals, optimal adversary, or real memecoin
calibration were implemented. Screening inputs are assumptions. Input fee
conventions differ slightly between the legacy-style surface (fee on reserve
difference) and the AMM (input fee); zero-fee controls isolate geometry and
fee-inclusive costs show actual implemented cashflows. Seed intervals quantify
only uncertainty within this assumed process. More data cannot turn those
assumptions into proven real-market behavior.
'''
    (ROOT/"PHASE2_FINDINGS.md").write_text(text,encoding="utf-8")
    validation=dict(status="complete",main_runs=len(raw),main_events=int(raw.events.sum()),
                    source_hashes_verified=True,all_summaries_recomputed=True,tests=count,
                    max_cash_error=max_cash,max_backing_error=max_back,
                    reproduced_terminal_states=60,executed_retail_exits=120,
                    maximum_exit_dust=float(exits.remaining_token_fraction.max()),
                    additional_exact_attack_profit=extra['attacker_profit_after_trading_fees'],
                    analysis_scripts_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                             (Path(__file__),ROOT/"scripts/verify_phase2_exits.py")},
                    csv_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.csv"))})
    (out/"report_validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
    figs=[px.bar(zero[zero.side=="buy"],x="architecture",y="executable_reference_notional_1pct",title="Executed model quotes: 1% local buy depth, zero fees / matched sponsor budget"),
          px.box(raw,x="architecture",y="arb_profit",facet_col="scenario",facet_col_wrap=2,title="Synthetic finite-market arbitrage cash gains, 50 seeds"),
          px.box(lp,x="scenario",y="lp_loss_vs_hodl",title="Shared AMM: external-marked LP loss relative to holding the seed portfolio"),
          px.bar(tox.reset_index().query("architecture in ['weighted','hub']"),x="architecture",y="cash_depletion_fraction",title="Executed finite toxic sale: common cash depletion"),
          px.line(bounded,x="tokens",y=["bounded_required","quadratic_required"],log_x=True,log_y=True,title="Mathematical backing at fixed per-asset issued fractions and coefficients")]
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><title>Phase 2: executed synthetic research</title><body><h1>Phase 2 research</h1><p>Synthetic cases and mathematical model calculations, not real market data. Read PHASE2_FINDINGS.md for budgets, rights and limits.</p>']
    for i,fig in enumerate(figs):parts.append(fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>')
    (out/"research_charts.html").write_text("\n".join(parts),encoding="utf-8")
    print(json.dumps({k:v for k,v in validation.items() if not k.endswith("sha256")},indent=2))


if __name__=="__main__":main()
