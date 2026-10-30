"""Source-checked copycat report. Verdict is chosen after inspecting actual data."""
from pathlib import Path
from dataclasses import fields
import argparse,hashlib,json,sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import plotly.express as px

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat.config import Variant


def money(x):return "n/a" if pd.isna(x) else (f"-${abs(x):,.2f}" if x<0 else f"${x:,.2f}")
def pp(x):return "n/a" if pd.isna(x) else f"{x*100:+.2f} pp"
def pct(x):return "n/a" if pd.isna(x) else f"{x:.1%}"
def table(head,rows):return "| "+" | ".join(head)+" |\n| "+" | ".join(["---"]*len(head))+" |\n"+"\n".join("| "+" | ".join(map(str,row))+" |" for row in rows)
def check_sources(manifest):
    assert manifest["status"]=="complete","Cannot report incomplete experiments"
    for name,digest in manifest.get("sources",{}).items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,"Source differs: "+name


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verdict",choices=("not_viable","viable_with_conditions","viable"),required=True)
    parser.add_argument("--base",default="research/copycat_diversion",help="Study bundle containing results/, controlled/, badge_controls/ and confirmation_controls/")
    args=parser.parse_args()
    base=ROOT/args.base;out=base/"results"
    m=json.loads((out/"manifest.json").read_text());check_sources(m)
    controlled=json.loads((base/"controlled/manifest.json").read_text());assert controlled["status"]=="complete"
    badges=json.loads((base/"badge_controls/manifest.json").read_text());check_sources(badges)
    strict_record=json.loads((base/"strict_badges/manifest.json").read_text());check_sources(strict_record)
    counter=json.loads((base/"confirmation_controls/manifest.json").read_text());assert counter["status"]=="complete"
    panel_record=json.loads((base/"wallet_panels/manifest.json").read_text());check_sources(panel_record)
    panel_summary=pd.read_csv(base/"wallet_panels/cohort_summary.csv")
    portfolio_record=json.loads((base/"portfolio_controls/manifest.json").read_text());check_sources(portfolio_record)
    portfolios=pd.read_csv(base/"portfolio_controls/confirmation.csv")
    raw=pd.read_csv(out/"confirmation_runs.csv");screen=pd.read_csv(out/"screen_runs.csv")
    summaries=pd.read_csv(out/"confirmation_summary.csv");rank=pd.read_csv(out/"confirmation_ranking.csv")
    srank=pd.read_csv(out/"screen_ranking.csv");allvars=pd.read_csv(out/"variants.csv")
    bestcontrols=pd.read_csv(base/"confirmation_controls/counterfactual_runs.csv")
    strict_badges=pd.read_csv(base/"strict_badges/strict_runs.csv")
    badge_raw=strict_badges[strict_badges.badge<.25]
    fronts=pd.read_csv(base/"controlled/front_response_search.csv")
    breakeven=pd.read_csv(base/"controlled/capital_race_break_even.csv")
    searches=pd.read_csv(out/"strategy_search.csv.gz")
    assert len(raw)==len(m["finalists"])*6*len(m["confirmation_seeds"])
    assert raw.groupby(["variant","family"]).seed.nunique().eq(len(m["confirmation_seeds"])).all()
    assert screen.groupby(["variant","family"]).seed.nunique().eq(len(m["screen_seeds"])).all()
    assert raw.initial_external_cash.nunique()==1
    # Verify key distribution point estimates directly from seed-level records.
    for key in ("attacker_profit","attacker_increment_vs_same_policy_control","original_consolidation_increment","retail_profit"):
        for (variant,family),g in raw.groupby(["variant","family"]):
            x=summaries[(summaries.variant==variant)&(summaries.family==family)&(summaries.metric==key)].iloc[0]
            assert np.isclose(x["mean"],g[key].mean(),rtol=1e-9,atol=1e-7)
            assert np.isclose(x["median"],g[key].median(),rtol=1e-9,atol=1e-7)
            assert np.isclose(x["q05"],g[key].quantile(.05),rtol=1e-9,atol=1e-7)
            assert np.isclose(x["q95"],g[key].quantile(.95),rtol=1e-9,atol=1e-7)
    testroot=ET.parse(base/"validation.xml").getroot()[0]
    assert testroot.attrib["errors"]=="0" and testroot.attrib["failures"]=="0"
    testcount=int(testroot.attrib["tests"])
    seen={(t.attrib.get("classname"),t.attrib["name"]) for t in testroot.findall("testcase")}
    extra=base/"badge_validation.xml"
    if extra.exists():
        suite=ET.parse(extra).getroot()[0]
        assert suite.attrib["errors"]=="0" and suite.attrib["failures"]=="0"
        seen.update((t.attrib.get("classname"),t.attrib["name"]) for t in suite.findall("testcase"))
        testcount=len(seen)
    # Attach independently searched zero-tax best responses to finalists.
    controls={}
    for row in allvars.to_dict("records"):
        v=Variant(**{f.name:row[f.name] for f in fields(Variant)})
        controls[row["variant"]]=v.control().label
    independent=[]
    portfolio_rows=[]
    for name,g in raw.groupby("variant"):
        ctrl=bestcontrols[bestcontrols.variant==controls[name]]
        assert len(ctrl)>0
        for family in ("race","spam","evasion","flip","front"):
            a=g[g.family==family].set_index("seed")
            b=ctrl[ctrl.family==family].set_index("seed")
            assert a.index.equals(b.index),"Unmatched independently optimized control seeds"
            assert np.array_equal(a.initial_external_cash,b.initial_external_cash),"Unequal capital budgets"
            richer=portfolios[(portfolios.variant==name)&(portfolios.family==family)]
            source="original independent search"
            if not richer.empty:
                b=richer.set_index("seed");assert a.index.equals(b.index)
                source="expanded voluntary-portfolio control"
            delta=a.attacker_profit-b.attacker_profit
            if not richer.empty:
                half=2.04523*delta.std(ddof=1)/np.sqrt(len(delta))
                portfolio_rows.append([name,family,pct(b.split.iloc[0]),money(a.attacker_profit.mean()),money(b.attacker_profit.mean()),
                                       money(delta.mean()),f"[{money(delta.mean()-half)}, {money(delta.mean()+half)}]"])
            independent.append(dict(variant=name,family=family,mean_difference=float(delta.mean()),median=float(delta.median()),
                                    q05=float(delta.quantile(.05)),q95=float(delta.quantile(.95)),min=float(delta.min()),max=float(delta.max()),control_search=source))
    optimized=pd.DataFrame(independent);optimized.to_csv(out/"independently_optimized_control_comparison.csv",index=False)
    ranked=[]
    for r in rank.itertuples():
        g=raw[(raw.variant==r.variant)&(raw.family!="none")]
        delta=optimized[optimized.variant==r.variant]
        ranked.append([r.variant,pp(r.original_consolidation_gain),money(r.original_absolute_liquidity_gain),
                       money(r.total_absolute_liquidity_gain),money(r.confused_buyer_pnl_change),money(r.vamper_pnl_change),
                       money(delta.mean_difference.max()),pct(g.original_leader_time_fraction.min())])
    attackrows=[]
    for family in ("race","spam","evasion","flip","front"):
        means=raw[raw.family==family].groupby("variant").attacker_increment_vs_same_policy_control.mean()
        name=means.idxmax();g=raw[(raw.variant==name)&(raw.family==family)]
        x=summaries[(summaries.variant==name)&(summaries.family==family)&(summaries.metric=="attacker_increment_vs_same_policy_control")].iloc[0]
        freq=summaries[(summaries.variant==name)&(summaries.family==family)&(summaries.metric=="profitable_attack_frequency")].iloc[0]
        attackrows.append([family,name,money(g.attacker_profit.mean()),money(g.attacker_profit.median()),money(x["mean"]),
                           f"[{money(x.mean_ci95_low)}, {money(x.mean_ci95_high)}]",pct(freq["mean"]),money(g.attacker_profit.max())])
    election_rows=[]
    for rule in ("first","threshold","held","volume"):
        g=raw[(raw.rule==rule)&(raw.family!="none")]
        if g.empty:continue
        defined=g.leader_final.notna()
        original=g.leader_final_is_original.astype(bool)
        actor=g.leader_final_is_attacker.astype(bool)
        election_rows.append([rule,pct(g.original_leader_time_fraction.mean()),pct(g.leader_defined_time_fraction.mean()),
                              pct(original.mean()),pct(actor.mean()),pct((defined&~original&~actor).mean()),pct((~defined).mean())])
    who=[]
    for form,burn,exit in (("creator","lock","never"),("holders","lock","never"),("buyer","lock","never"),
                           ("burn","lock","never"),("burn","supply","never"),("treasury","lock","never"),("treasury","lock","first")):
        g=raw[(raw.form==form)&(raw.burn==burn)&(raw.treasury_exit==exit)&(raw.family=="none")]
        if g.empty:continue
        label=form+(" ("+burn+")" if form=="burn" else " (exit="+exit+")" if form=="treasury" else "")
        who.append([label,money(g.creator_diversion_receipts.mean()),money(g.holder_dividend_receipts.mean()),
                    money(g.creator_original_profit.mean()),money(g.confused_increment_vs_control.mean()),
                    money(g.early_leader_mean_pnl.mean()),money(g.late_leader_mean_pnl.mean()),
                    money(g.early_copy_mean_pnl.mean()),money(g.late_copy_mean_pnl.mean())])
    frontrows=[]
    for form,burn in (("creator","lock"),("holders","lock"),("buyer","lock"),("treasury","lock"),("burn","lock"),("burn","supply")):
        g=fronts[(fronts.form==form)&(fronts.burn==burn)];r=g.loc[g.profit.idxmax()]
        frontrows.append([form+(" ("+burn+")" if form=="burn" else ""),money(r.profit),money(r.leader_cap),
                          money(r.copy_buy_budget),pct(r.rate),money(r.capital_committed),int((g.profit>0).sum())])
    # Same-intensity display controls are a separate searched/evaluated experiment.
    badge_rows=[]
    for r,g in badge_raw[badge_raw.family=="none"].groupby(["rule","badge"]):
        badge_rows.append([r[0],pct(r[1]),pp(g.original_consolidation_increment.mean()),money(g.original_absolute_liquidity_increment.mean()),
                           money(g.retail_increment_vs_control.mean()),money(g.confused_increment_vs_control.mean()),money(g.vamp_increment_vs_control.mean())])
    bankrows=[]
    for r in breakeven[breakeven.rate==.05].itertuples():
        bankrows.append([money(r.leader_threshold),money(r.entry_capital),money(r.roundtrip_curve_fees),money(r.outsider_spending_break_even)])
    # Different configurations within a form are not a single treatment. These
    # screen winners are identifiers, not pooled evidence of a globally best rule.
    core=[]
    for rule,window,threshold in (("first",30,100000),("threshold",30,100000),("threshold",30,1000000),
                                 ("held",5,100000),("held",30,100000),("held",120,100000),
                                 ("volume",5,100000),("volume",30,100000),("volume",120,100000)):
        for form in ("creator","holders","buyer","burn"):
            subset=srank[(srank.rule==rule)&(srank.form==form)&(srank.window==window)&(srank.threshold==threshold)]
            if subset.empty:continue
            r=subset.iloc[0]
            core.append([r.variant,pp(r.original_consolidation_gain),money(r.original_absolute_liquidity_gain),
                         money(r.worst_mean_incremental_attack_gain),pct(r.worst_original_identity_fraction)])
    pd.DataFrame(core,columns=["configuration","original_share_gain","original_liquidity_gain","max_incremental_attack","minimum_original_leader_fraction"]).to_csv(out/"leader_form_screen_frontier.csv",index=False)
    worst=raw.loc[raw.attacker_profit.idxmax()]
    confusionworst=raw.loc[raw.confused_mean_profit.idxmin()]
    maxcash=max(raw.cash_conservation_error.max(),screen.cash_conservation_error.max())
    maxback=max(raw.reserve_backing_error.max(),screen.reserve_backing_error.max())
    mincash=min(raw.minimum_wallet_cash.min(),screen.minimum_wallet_cash.min())
    default=rank[rank.variant=="first_buyer_5pct_exact_fixed_badge0"].iloc[0]
    best_financial=rank[rank.form!="control"].iloc[0]
    nominal=[]
    for rate in (.01,.03,.05,.1):
        for label,data in (("Buyer-owned diversion",screen[(screen.rule=="first")&(screen.form=="buyer")&(screen.rate==rate)&(screen.matching=="exact")&(screen.family=="none")]),
                           ("Display steering",badge_raw[(badge_raw.rule=="first")&(badge_raw.badge==rate)&(badge_raw.family=="none")])):
            nominal.append([label,pct(rate),pp(data.original_consolidation_increment.mean()),money(data.original_absolute_liquidity_increment.mean()),
                            money(data.retail_increment_vs_control.mean())])
    fixed_cohort=[]
    for row in panel_summary[(panel_summary.cohort=="fixed_confused")&(panel_summary.metric=="cash_pnl_change_mean")].itertuples():
        fixed_cohort.append([row.variant,money(row.mean),f"[{money(row.mean_ci95_low)}, {money(row.mean_ci95_high)}]",int(row.n)])
    version={"not_viable":"**Not viable as a mandatory, permissionless, ticker-defined consolidation mechanism.**",
             "viable_with_conditions":"**Viable with conditions, within the disclosed model; general permissionless safety is not demonstrated.**",
             "viable":"**Viable within the tested model and disclosed constraints; real-market validation remains outstanding.**"}[args.verdict]
    text=f'''# Copycat diversion ("vamps feed the leader"): findings

29 October 2026. Off-chain **synthetic research**, not historical market evidence.
Read [DESIGN.md](DESIGN.md) for definitions written before implementation and
[README.md](README.md) for commands, data fields and limitations.

## Clarified objective: whichever token wins

The user clarified that success means concentration on **any enduring ticker
winner**, including a copy. Original survival is not required. The original-
focused ranking and verdict below therefore do not settle that objective.
Read [WINNER_REANALYSIS.md](WINNER_REANALYSIS.md) for the corrected interpretation,
identity-free concentration comparisons and remaining uncertainties. The earlier
analysis is retained for audit; its accounting and measured cash flows stand.

## Earlier verdict, retained with its original scope

{version}

The useful distinction is between a creator/holder transfer, a buyer-owned
portfolio split, and non-redeemable price support. They are not interchangeable
liquidity improvements. The results below rank actual accessible redemption,
who bears the cost, identity capture and incremental adversarial profit against
matched controls. A higher named-leader share alone is not sufficient evidence.

Buyer-owned routing to an independently verified original remains a conditional
product hypothesis: the buyer retains both funded assets. The present ticker
rules are not an identity oracle, and large automatic leader orders expose the
buyer to ordering extraction. Treasury ownership is a different economic right.
Display/provenance steering is a control worth validating with real users; its
assumed steering percentages are not observed behavioral effectiveness.

The default first-launch/buyer-owned 5% setting increased original accessible-
liquidity share by **{pp(default.original_consolidation_gain)}** and its time-averaged
accessible redemption by **{money(default.original_absolute_liquidity_gain)}** in
confirmation. Total accessible redemption changed by
{money(default.total_absolute_liquidity_gain)}, aggregate retail cash P&L by
{money(default.retail_pnl_change)}, and confused-buyer mean cash P&L by
{money(default.confused_buyer_pnl_change)}. This is real redistribution of funded
claims, with mixed distributional effects, rather than new liquidity creation.

The largest confirmed financial share increase was
`{best_financial.variant}`: {pp(best_financial.original_consolidation_gain)},
with {money(best_financial.original_absolute_liquidity_gain)} more original
accessible redemption and a {money(best_financial.confused_buyer_pnl_change)}
change in mean cash P&L for confused buyers. Its fixed-volume identification also benefits
from the original's deterministic early-address head start. The conditional
buyer-owned candidate should not be dismissed using a restricted-control spam
comparison; the stronger comparison below materially changes that attribution.

## What actually ran

- **{testcount} project tests passed**; reference paths reuse the original Decimal
  independent engine and the existing curve fee. Cash funding, payouts, burn
  accounting, first-address volume, dwell/cooldown, evasion, and the repeated
  budget-depletion failure have regression coverage.
- Main grid: **{m['variants']} settings**, including the 144 leader/form/rate core
  and declared robustness/ownership/badge controls. It is not every possible
  combination of all knobs.
- Attack policies were selected on **{m['training_seeds']}**, {m['training_events']}
  buyer arrivals, separately for each variant/family. Search export contains
  **{len(searches):,} candidate evaluations** (including reused abstention scores).
- Screening used **{len(m['screen_seeds'])} distinct held-out seeds**,
  {m['screen_events']} arrivals per market. Confirmation used **{len(m['confirmation_seeds'])}
  fresh seeds** and {m['confirmation_events']} arrivals for {len(m['finalists'])}
  selected settings. Attack policies were not retuned on these confirmation seeds.
- The main workflow executed **{m['actual_market_executions']:,} market calls /
  {m['actual_demand_events']:,} organic-arrival events**, including training,
  matched counterfactuals and recorded examples, in {m['elapsed_seconds']:.1f}
  elapsed seconds (including the preserved serial training prefix). Deterministic
  worker processes completed the remaining calls, after bit-identical serial/
  parallel validation. Exact-call cache hits and repeated idle policies are not
  extra independent observations.
- {controlled['cases']} independent funded large-order response searches validated
  realized cash against the analytic prediction, with fees, gas, minimum output
  and abstention. Separately searched small-badge controls and independently
  optimized zero-tax confirmation opponents are also saved.
- Individual no-attack panels add {panel_record['actual_market_executions']:,}
  source-checked market calls and {panel_record['wallet_records']:,} matched wallet
  records, reproducing confirmed retail totals. Wallets are not independent markets.
- A further {portfolio_record['actual_market_executions']:,} calls broadened buyer-route
  spam/evasion controls to voluntarily buy leader-token portfolios, using the
  original training seeds and untouched confirmation seeds.
- {strict_record['variants']} badge settings were independently retrained/retested
  with steering disabled until an elected leader exists. This corrects the
  original-to-undefined-leader fallback for delayed badge rules, with
  {strict_record['actual_market_executions']:,} additional market calls.
- Source hashes, completion states and key seed summaries were checked again
  before this report. The failed development search is preserved and excluded.

All stages span 240 simulated minutes. Total intended organic notional is $600k,
organic starting capital $1m, and the attacker has $1.1m **across** its aliases.
Initial world funding is $2.225m, unchanged by the variant. Each organic arrival
has its own funded wallet; scheduled and terminal exits determine actual P&L.
The original launches first; 14 ordinary copies arrive later, and attack policies
can launch a main plus up to 24 additional copies. Pre-squatting before the true
original is excluded. Confusion is 35%; informed share 20%; launch cost $10;
network expense $.05 per curve operation; curve fee .3%.

Training, screening and confirmation have different arrival resolution/per-wallet
cash limits. They are separate experiments; do not pool their returns or interpret
their differing attack opportunities as statistical replication of one design.
This matters particularly for front-running large orders.

## Exact results: what the mechanism actually pays for

Let rho=(1-f)/(1+f), budget B, diversion D=alpha B.
Every token still has `p_i=p0+k q_i`, with unchanged own slope k and zero
cross-token price derivative. Any consolidation comes from redirecting funded
order flow or attention; no variant creates a new shared reserve or deeper
curve merely by attaching a ticker label.

1. **Creator/holder cash transfers** leave `rho(1-alpha)B` as an isolated copy
   position's immediate redemption versus `rho B` without diversion. The recipient
   gets D; the leader's curve does not automatically receive new backing.
2. **Buyer-owned routing** gives the same buyer two fully funded positions.
   Combined immediate redemption is `rho B` before network expense, if nobody
   else trades. It reallocates exposure, rather than giving away that whole share
   of the buyer's capital. Subsequent relative token performance/order matters.
3. **Never-selling treasury versus buy-and-lock:** their public price/redemption
   paths match under the tested policies. Treasury retains a redemption option and
   overhang risk; the locked address does not. Buying tokens for existing holders
   is already the holder-payout variant, not a third ownership interpretation.
4. **Literal reduction of pricing supply** restores the pre-buy price. Retained
   collateral becomes a surplus with no invented holder payout right. Treating
   that surplus as deeper usable leader liquidity would be a measurement error.
5. **Self-paid creator diversion is not revenue:** a funded own-copy round trip
   nets `-(1-rho)(1-alpha)B`, before launch/gas. Wallet splitting cannot make
   self-paid cash an outside subsidy.

If an actor captures fraction phi of outsiders' copy spending V through direct
diversions, break-even requires
`phi alpha V + other realized trading gains > launches + election cost + wash losses`.
For phi=1 and 25 actor tokens, launch fees alone require outside spending of
$25,000/$8,333/$5,000/$2,500 at 1%/3%/5%/10%. These are conditional arithmetic,
not a claim about organic adoption; own washing is excluded from V.

Quoted-cap threshold races distinguish **reusable bankroll** from net expense:

{table(['Cap threshold','Entry cash required','No-external-trade round-trip fees','Outside taxed spend to cover costs at 5%'],bankrows)}

The calculation includes the $10 launch and $.10 two-transaction expense in its
break-even spending. Holding/market interaction can add cost or profit; no borrowing
or capital opportunity cost is modeled. A fixed title may survive its qualifying
pump being fully unwound. That is a financial entitlement design issue even when
the reserve remains solvent.

## Ranking table: held-out finalists

Rows are separately evaluated configurations. Share changes are percentage points
of time-averaged **actual original** private-holder redemption, relative to the
same rule/matcher without diversion. Dollar columns expose denominator-only
"consolidation." Attack Δ compares each configuration with the matched control's
**independently training-selected** policy in the same family, then takes the
worst tested family mean. Buyer-route spam/evasion use the expanded voluntary-
portfolio control below. This is a stress envelope, not a globally optimal policy.

{table(['Configuration','Δ original share','Δ original accessible $','Δ total accessible $','Δ confused buyer mean P&L','Δ fixed vamper P&L','Worst mean extra attack profit','Minimum original-leader time'],ranked)}

The complete screen ranking and leader/form frontier are in `results/screen_ranking.csv`
and `results/leader_form_screen_frontier.csv`; every rate and window is retained.
No apparent winner is certified safe merely because this finite search found
no profitable intervention. Thresholds that rarely choose any leader are not
credited as successful protection.

| Leader rule | Research interpretation |
| --- | --- |
| First launched | Clearest candidate for buyer-owned routing **when chronology is an acceptable identity rule**. Original correctness is assumed through launch order; near-ticker groups still fragment, and original-holder/retail welfare is mixed. |
| Cap threshold | A reversible pump can acquire a persistent entitlement and informed flow. The tested capture policies materially worsen outcomes; large qualifying bankroll is not the same as permanent attack expense. |
| Sustained cap lead | Dwell adds time/capital exposure, but tested races still capture the title and profit. Longer windows can also leave the title undefined for much of a short viral event. |
| Distinct-address volume | Fixed early selection performed better in this tape, where funded original snipers qualify first. It is not an identity or Sybil-resistance result; flipping and late qualification need separate safeguards. |

Cash creator/holder forms do not add original-curve dollars. Buy-and-lock produces
larger measured original claims for remaining holders at copy buyers' expense.
Treasury exit retains the pre-exit consolidation statistic while later reducing
retail cash; it cannot be credited with both permanent locking and recoverable
protocol capital. Buyer ownership is the least confiscatory financial form here.

## Adaptive attacks: best found within each policy class

Each family includes no action. Policies search actual funding, timing, residual
inventory, aliases/spam counts and ticker strings. Volume attacks use funded
addresses; held-cap attacks keep a real quote lead; front-runs optimize against
the relevant payout or leader leg. Fixed-title impossibilities and creator-only
front-runs can optimally abstain. The worst-family display below chooses a
configuration *after* evaluating the stress set; use the individual per-setting
distributions in `confirmation_summary.csv` for inference.

{table(['Attack','Setting with largest mean extra gain','Mean cash profit','Median','Mean Δ vs same-policy no-tax control','95% Δ interval','Profitable runs','Maximum observed cash profit'],attackrows)}

The search space is disclosed in `attacks.py` and all candidate scores in
`strategy_search.csv.gz`. Search is not globally exhaustive, including possible
joint attacks, longer strategies, more spellings or different identity systems.
Search-selection uncertainty is not included in the displayed mean intervals.
Ordinary copy-launch trading gains already available without diversion are
separated from incremental diversion gains; the fixed single-copy vamper is
reported separately from the adaptive, well-funded attacker.
In particular, adding visible copies increases an actor's share of uniform
confused impressions even in the no-diversion model. That attention assumption
can make copy spam profitable on its own; the matched increments distinguish
that source of profit from collecting a new diversion entitlement.

### Control-policy breadth changes the spam attribution

The main search's zero-tax copy-spam strategy bought only its copy positions.
Buyer-owned diversion also gave that actor a leader position. It would be unfair
to describe every resulting profit difference as a new, unreplicable exploit.
The additional control searches voluntary leader splits of 0%,1%,3%,5%,10% on
the actor's own buys, charging the same fees/gas. Outsider buys remain undiverted.
It trains independently for spam/evasion on the same original training seeds:

{table(['Buyer-route setting','Family','Selected control split','Variant mean cash profit','Expanded control mean','Mean difference','95% difference interval'],portfolio_rows)}

The apparent default first/5% **spam** uplift against the narrow control does not
survive this stronger comparison. It is not evidence of a novel copy-spam exploit.
This is a conservative attribution check that broadens the control's options;
it does not symmetrically optimize every possible portfolio under the diversion
variant or establish a global best response. Both sets of records are retained.

### Large pending copy buys: controlled best-response search

Small-wallet Monte Carlo non-profitability is not a proof against this attack.
For a diverted buy budget D, the victim's leader quantity is the exact inverse
at the front-run price p+kb. Gross attacker gain is `k b d(b)`, not a quantity
assumed unchanged by the attack. Holder dividends instead give
`D b/(q+b)`, less round-trip fees. Pure creator cash transfer gives no such
inventory-buy reward. Literal supply destruction cancels the price increment.

The funded control uses leader caps $2k/$100k/$1m, copy buy budgets
$10k/$100k/$500k, all four rates and the ownership/burn interpretations. Each
response compares 65 golden-section iterations, 100 logarithmic sizes and idle.
The leader-buy leg enforces at least 98% of its pre-attack output. Maxima within
this **controlled grid**, including trading fees and $.10 attacker network cost:

{table(['Form','Best cash profit','Leader cap','Copy buy budget','Rate','Cash committed','Positive cases'],frontrows)}

These are executed synthetic stress cases, not estimated real-world probabilities.
They isolate front-running of the **leader leg**. Public independent-curve buys
are also order-sensitive; this search does not compare the best combined
copy-and-leader sandwich with the best sandwich of an undiverted copy order.
Leader-leg extraction therefore establishes an exposure, not a measured increase
in total MEV over every possible independent-curve control strategy.
The treasury-never-sells and buy-and-lock response agree; a later treasury sale
would create overhang. Existing holders receiving cash is a snapshot entitlement
and can be bought just before the payout. The contracts' continued solvency does
not prevent any of these transfers from a paying copy buyer.

## Identity, ticker matching and copy spam

The headline leader is the leader of the original's matching group. Near-ticker
groups can have their own attacker leaders; they remain in the campaign's total
liquidity/volume denominator. `attacker_led_groups_liquidity_share_time_mean` and
`original_matching_group_share_time_mean` expose that fragmentation instead of
quietly excluding unrecognized copies. All spelling candidates are assumed
semantically related in this synthetic market, including out-of-radius strings.

{table(['Rule among confirmed cases','Mean original-leader time','Mean defined-leader time','Final real original','Final attacker','Final ordinary copy','Final undefined'],election_rows)}

First-launch identification is correct **by the launch-order assumption** here;
it does not establish real authorship. Fixed volume selection also benefits from
an early original with multiple snipers/organic addresses. This is not evidence
of Sybil-resistant identity. Held caps can be supported with recoverable capital;
distinct wallet addresses can be bundled; a cooldown delays changes but can
preserve a captured title while its inventory is unwound.
In this tape, the original has four funded sniper addresses before age five;
fixed distinct-wallet election can lock it before any post-launch attacker token
reaches minimum age. Its low measured capture rate relies on that head start,
not on the distinct-address score being a Sybil-resistant identity test.

Exact matching is evaded by case or whitespace, case folding by other spellings,
and the declared fuzzy rule by out-of-radius/homoglyph candidates. The economic
success of an evasive string depends on human confusion: equal synthetic
visibility is an assumption, not evidence that ELONXX is as persuasive as ELON.
Fuzzy false positives against unrelated legitimate tickers were not modeled.
Pure string rules cannot certify which independently launched asset is authentic.

## Who pays, who gains, and timing

These form-level rows are **descriptive averages across selected settings**, not
one pooled treatment or a causal estimate. Cohorts are defined by purchase time
and intended leader/copy target; buyer-owned diversion can add a second asset.
P&L is actual final cash after funded exits, fees, launch/network costs and cash
payments. The matched increments and configuration-specific cohort distributions
are provided in the CSVs.

{table(['Form','Creator cash diversion','Holder cash dividends','Original creator P&L','Δ confused buyer mean','Early leader mean','Late leader mean','Early copy mean','Late copy mean'],who)}

Worst observed confirmed actor cash profit was {money(worst.attacker_profit)}
(`{worst.variant}`, family `{worst.family}`, seed {int(worst.seed)}). The worst
observed confused-buyer *cohort mean* was {money(confusionworst.confused_mean_profit)}
in `{confusionworst.variant}`, seed {int(confusionworst.seed)}. These are sample
extrema, not bounds or individual-buyer worst cases. Creator/holder receipts
include their entitlements; external attacker receipts separately exclude
self-funded payouts. No capital is created by the independent reserve potential.

Matched wallet panels hold the *control's confused-wallet membership* fixed.
They therefore also capture buyers a badge steers out of confusion, avoiding a
changing-cohort comparison. No-attack per-buyer mean cash changes, with intervals
across seeds rather than pooled wallet observations:

{table(['Configuration','Fixed confused cohort mean Δ','95% mean interval','Seeds'],fixed_cohort)}

Across these no-attack individual panels, the worst individual realized cash P&L
was {money(panel_record['minimum_individual_pnl'])}; the worst individual matched
change was {money(panel_record['minimum_matched_change'])}. Those are distinct
sample extrema and need not be the same wallet. Full early/middle/late, intended
leader/copy, median, tail and matched-change records are in
`wallet_panels/wallets.csv.gz`, `seed_cohorts.csv` and `cohort_summary.csv`.

## Display-only comparison at low steering shares

**Badge audit:** the original simulator lets badge-selected impressions fall back
to the original when no leader qualifies. That grants delayed-rule badges useful
information before the election. Those raw records are preserved, but are not
used as evidence for a delayed elected badge. `strict_badges/` retrains all 27
high-steering and 16 low-steering controls with zero badge steering until a
leader is defined; informed traders retain their explicitly assumed original
fallback. The table below uses these strict runs. First-launch badges always
have a leader, and a regression test confirms their paths are identical.
The main screen ranking retains the legacy delayed-badge rows for audit; the
confirmed badge finalist is first-launch and is unaffected. Do not pool the two
definitions or use legacy rows as proof of an elected badge's effectiveness.

A 25% badge is not a fair substitute for assuming a 1% diversion has the same
behavioral reach. The separate controls below therefore also use nominal
steering shares of 1%,3%,5%,10%, independently searched on the training seeds.
Steering probability and dollar allocation are still different interventions,
so these are transparent scenarios, not empirically matched persuasion costs.

{table(['Leader rule','Assumed badge steering','Δ original share','Δ original accessible $','Δ total retail P&L','Δ remaining confused-buyer mean','Δ fixed vamper P&L'],badge_rows)}

These controls grant no creator/holder entitlement and no mandatory secondary
leader order. They still depend on leader identification and assumed user
response, and a manipulable badge can steer users toward an attacker too.
Badge steering also changes which wallets remain confused: that column compares
the remaining confused cohorts, not the same individuals' causal treatment effect.
The total-retail column retains the same funded population across each pair.
Verified provenance versus a financially elected badge is an untested product
choice. A field/user study would be needed to quantify actual confusion reduction.

For the same six screening seeds, first-launch buyer routing and first-launch
display controls at equal **nominal** percentages were:

{table(['Intervention','Nominal rate','Δ original share','Δ original accessible $','Δ total retail P&L'],nominal)}

This is a within-stage comparison, avoiding the different confirmation wallet
sizes. A steering probability is still not the same intervention as a dollar
allocation fraction. The display scenario's favorable results are conditional
on those behavioral probabilities, not proof of real-world persuasion dominance.

## Conservative interpretation and conditions

- Creator/holder payments are distributions, not automatic leader-reserve deposits.
  A higher reserve share from draining copies is not new absolute liquidity.
- Buyer-owned splitting is the closest variant to the stated consolidation goal
  while preserving the buyer's funded claims. It requires justified leader identity,
  explicit ownership/consent, output protection and an ordering policy before a
  safety claim. Those mitigations are conditions to test, not proven fixes here.
- A never-selling treasury is close to permanent locking, with additional future
  redemption/overhang risk. Literal supply burn is different and mainly leaves
  a surplus rather than maintaining the funded buy's price effect.
- A quoted-cap or address-volume title is not proof of authenticity. Fixed titles,
  flippable titles and cooldowns trade different capture/entrenchment risks.
- Any finite matching boundary can leave semantic copies outside the levy. If
  confused demand migrates there, the scheme can create royalty farms or evasion
  incentives instead of one authentic liquidity pool.

The result does not establish that every opt-in portfolio-split product is bad,
nor that every real memecoin market behaves like these wallets. It does separate
the original consolidation claim from irreversible transfers, selection capture,
predictable-order MEV and simple display steering. The general mandatory mechanism
has not earned a permissionless safety or welfare claim from these experiments.

## Accounting evidence and limits

Largest recorded cash-conservation error across screen/confirmation:
{maxcash:.6g} USDC; largest backing error {maxback:.6g} USDC; minimum wallet cash
{mincash:.6g} USDC. These float discrepancies are scoped to the research tolerance;
the reference ledger enforces exact Decimal funded accounting. The funding-boundary
defect found during development was fixed and regression-tested, not suppressed.
Residual unprofitable-to-redeem token dust is exported; it is not valued as cash.

Mean intervals use seed-level t critical values (screen n={len(m['screen_seeds'])},
confirmation n={len(m['confirmation_seeds'])}); attack success intervals use Wilson
binomial intervals. Quantiles and minima/maxima are in the summaries. These quantify
uncertainty inside this assumed process, not model uncertainty or global attack
optimality. Ranked settings/families involve selection; per-family intervals do
not correct for that selection. Screening and confirmation are never pooled.

The model has no external exchange, supply allocations, real meme utility,
endogenous demand elasticity, identity attestations, pre-squatting, latency race,
gas auction or enforcement against other launchpads. It assumes atomic routing
and publicly observable pending large orders. All participants are funded and
own what they sell. Confirmation has more smaller wallets than training; the
large-order control prevents treating that wallet-size choice as an MEV defense.

## Reproduce

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q --junitxml=research/copycat_diversion/reproduce/validation.xml
.\\.venv\\Scripts\\python.exe scripts/copycat_parallel.py --out research/copycat_diversion/reproduce/results --workers 6
.\\.venv\\Scripts\\python.exe scripts/copycat_controlled_attacks.py --out research/copycat_diversion/reproduce/controlled
.\\.venv\\Scripts\\python.exe scripts/copycat_badge_controls.py --out research/copycat_diversion/reproduce/badge_controls
.\\.venv\\Scripts\\python.exe scripts/copycat_confirmation_controls.py --study research/copycat_diversion/reproduce/results --out research/copycat_diversion/reproduce/confirmation_controls --all-controls --workers 6
.\\.venv\\Scripts\\python.exe scripts/copycat_wallet_panels.py --study research/copycat_diversion/reproduce/results --out research/copycat_diversion/reproduce/wallet_panels --workers 6
.\\.venv\\Scripts\\python.exe scripts/copycat_portfolio_controls.py --base research/copycat_diversion/reproduce --workers 6
.\\.venv\\Scripts\\python.exe scripts/copycat_strict_badges.py --out research/copycat_diversion/reproduce/strict_badges --workers 6
Copy-Item research/copycat_diversion/DESIGN.md,research/copycat_diversion/README.md -Destination research/copycat_diversion/reproduce
.\\.venv\\Scripts\\python.exe scripts/build_copycat_report.py --base research/copycat_diversion/reproduce --verdict {args.verdict}
```

The standalone plots are `results/research_charts.html`. All candidate definitions,
chosen policies, seed records, cohorts, examples and manifests are included. The
fresh bundle paths preserve the original evidence. The verdict flag records the
research judgment after inspection; it does not alter statistics. See README for
smaller smoke runs and configurable
confusion, informed share, attacker budget, launch fee and network expense.
'''
    (base/"FINDINGS.md").write_text(text,encoding="utf-8")
    validation=dict(status="complete",verdict=args.verdict,tests=testcount,
                    verdict_scope="earlier original-focused interpretation; insufficient for clarified any-winner convergence goal",
                    full_suite_tests=int(testroot.attrib["tests"]),additional_unique_tests=testcount-int(testroot.attrib["tests"]),
                    confirmed_rows=len(raw),screen_rows=len(screen),main_market_calls=m["actual_market_executions"],
                    source_hashes_verified=True,selected_summary_estimates_verified=True,
                    maximum_cash_error=maxcash,maximum_backing_error=maxback,minimum_wallet_cash=mincash,
                    report_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    files={p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(list(out.glob("*.csv"))+[p for folder in ("controlled","badge_controls","confirmation_controls","wallet_panels","portfolio_controls","strict_badges")
                                                                     for p in (base/folder).glob("*.csv*")])})
    (base/"report_validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
    financial=rank[rank.form!="control"]
    figures=[px.bar(financial,x="variant",y="original_consolidation_gain",title="Synthetic confirmation: change in original accessible-liquidity share"),
             px.box(raw[raw.family!="none"],x="family",y="attacker_increment_vs_same_policy_control",color="form",title="Incremental attacker cash P&L; separate confirmed configurations"),
             px.scatter(pd.concat([screen[~((screen.form=="control")&(screen.badge>0))],strict_badges]).query("family == 'none'").groupby(["variant","form"],as_index=False)[["original_consolidation_increment","original_absolute_liquidity_increment"]].mean(),
                        x="original_consolidation_increment",y="original_absolute_liquidity_increment",color="form",title="Share gain versus absolute original liquidity gain: denominator effects"),
             px.box(raw[raw.family=="none"],x="form",y="confused_increment_vs_control",title="Confused-buyer cash P&L change versus matched zero diversion"),
             px.scatter(fronts,x="copy_buy_budget",y="profit",color="form",facet_col="leader_cap",log_x=True,title="Controlled large-order optimized front-runs, funded and fee-inclusive")]
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><title>Copycat diversion research</title><body><h1>Executed synthetic copycat-diversion research</h1><p>Not historical market data. Read FINDINGS.md for budgets, ownership, matching, search and uncertainty limits.</p>']
    for i,fig in enumerate(figures):parts.append(fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>')
    (out/"research_charts.html").write_text("\n".join(parts),encoding="utf-8")
    print(json.dumps({k:v for k,v in validation.items() if k!="files"},indent=2))


if __name__=="__main__":main()
