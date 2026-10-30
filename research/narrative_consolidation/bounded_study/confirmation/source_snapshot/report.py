"""Descriptive and paired analysis of completed frozen experiments only."""
from dataclasses import asdict
from pathlib import Path
import json,math,hashlib
import numpy as np
import pandas as pd
from .experiments import fresh,write_json


def ci(values,key='fixed'):
    a=np.asarray(values,dtype=float);a=a[np.isfinite(a)]
    if len(a)==0:return float('nan'),float('nan'),float('nan')
    rng=np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big'))
    boot=a[rng.integers(0,len(a),size=(2000,len(a)))].mean(axis=1)
    return float(a.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))


def wilson(k,n):
    z=1.95996398454;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return mid-radius,mid+radius


def markdown(frame,columns):
    def value(x):
        if isinstance(x,(float,np.floating)):return f'{x:.3f}' if math.isfinite(x) else 'N/A'
        return str(x)
    lines=['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
    for _,r in frame.iterrows():lines.append('| '+' | '.join(value(r[k]) for k in columns)+' |')
    return '\n'.join(lines)


def build_report(root):
    manifest=json.loads((root/'confirmation/manifest.json').read_text())
    if manifest['status']!='complete':raise ValueError('Cannot issue complete findings for incomplete confirmation')
    plan=json.loads((root/'frozen_plan.json').read_text())
    data=pd.read_csv(root/'confirmation/runs.csv.gz');out=fresh(root/'analysis')
    metrics=['cohort_reserve','winner_reserve','winner_depth_500','cohort_depth_500','organic_active',
             'executed','offered','outside_spent','abandoned_unexecuted','trader_cash_change','creator_pnl',
             'support_claims','refunds','realized_acceptance','winner_price','winner_cap']
    summary=[];paired=[]
    for (name,label),g in data.groupby(['name','label']):
        for metric in metrics:
            vals=g[metric].dropna().to_numpy()
            if not len(vals):continue
            mean,lo,hi=ci(vals,f'{name}:{label}:{metric}')
            summary.append(dict(name=name,label=label,metric=metric,n=len(vals),mean=mean,mean_low=lo,mean_high=hi,
                                median=float(np.median(vals)),p05=float(np.quantile(vals,.05)),p95=float(np.quantile(vals,.95))))
    sf=pd.DataFrame(summary);sf.to_csv(out/'distributions.csv',index=False)
    indexed=data.set_index(['name','label','seed'])
    for target in plan['targets']:
        name=target['name']
        controls=['A'] if target['kind']=='no_attack' else [target['base']]
        if name.startswith('D') or name=='SINGLE_BATCH':controls+=['INDEPENDENT_BATCH','SINGLE_BATCH']
        for control in set(controls)-{name}:
            for label in ('plus_1h','plus_24h','plus_7d','feasible_exit','before_unlock','after_unlock'):
                g=indexed.loc[(name,label)].sort_index();base=indexed.loc[(control,label)].sort_index()
                for metric in ('cohort_reserve','winner_reserve','winner_depth_500','cohort_depth_500','organic_active','trader_cash_change','creator_pnl'):
                    delta=g[metric]-base[metric];mean,lo,hi=ci(delta,f'{name}:{control}:{label}:{metric}')
                    paired.append(dict(name=name,control=control,label=label,metric=metric,n=len(delta),
                                       mean_delta=mean,low=lo,high=hi))
    pf=pd.DataFrame(paired);pf.to_csv(out/'paired_differences.csv',index=False)
    threshold=[]
    for target in plan['targets']:
        name=target['name'];c=target['config']
        if name not in ('C','C_MIGRATE_0') and not name.startswith(('C_ACCEPT_','C_ROUTING_ONLY_')):continue
        g=indexed.loc[(name,'plus_7d')]
        delta=pf[(pf.name==name)&(pf.control=='A')&(pf.label=='plus_7d')&(pf.metric=='cohort_reserve')].iloc[0]
        threshold.append(dict(name=name,grid='routing_only' if c['migration']==0 else 'with_migration',assumed_acceptance=c['acceptance'],reach=c['reach'],migration=c['migration'],
                              realized_quote_acceptance=g.authorized.sum()/g.reachable.sum() if g.reachable.sum() else 0,
                              capital_delta=delta.mean_delta,low=delta.low,high=delta.high))
    tf=pd.DataFrame(threshold).sort_values('assumed_acceptance');tf.to_csv(out/'acceptance_grid.csv',index=False)
    attack=[]
    for target in plan['targets']:
        if target['kind']!='trained_attack':continue
        g=indexed.loc[(target['name'],'feasible_exit')].sort_index();base=indexed.loc[(target['base'],'feasible_exit')].sort_index()
        profit=g.attacker_cash_pnl;mean,lo,hi=ci(profit,target['name'])
        complete=g.attacker_residual.eq(0);positive=profit.gt(0)&complete;k=int(positive.sum());wil=wilson(k,len(g))
        loss=base.trader_cash_change-g.trader_cash_change
        attack.append(dict(name=target['name'],base=target['base'],mean_profit=mean,low=lo,high=hi,
                           profit_frequency=k/len(g),frequency_low=wil[0],frequency_high=wil[1],
                           complete_exits=int(complete.sum()),mean_peak=g.attacker_peak.mean(),mean_fees=g.attacker_fees.mean(),
                           mean_other_trader_loss=loss.mean(),max_profit=profit.max(),min_profit=profit.min(),
                           mean_capital_days=g.attacker_capital_days.mean(),mean_opportunity_cost=g.attacker_opportunity_cost_10pct.mean()))
    af=pd.DataFrame(attack);af.to_csv(out/'attack_confirmation.csv',index=False)
    primary=['A','B','B_CREATOR','B_DESTROY','B_CREATOR_DESTROY','C','D','SINGLE_SPOT','SINGLE_BATCH','INDEPENDENT_BATCH','SPOT_LOCK']
    primary_rows=[]
    for name in primary:
        for label in ('plus_1h','plus_24h','plus_7d'):
            g=indexed.loc[(name,label)]
            primary_rows.append(dict(name=name,checkpoint=label,cohort=g.cohort_reserve.mean(),winner=g.winner_reserve.mean(),
                                     depth5=g.winner_depth_500.mean(),active=g.organic_active.mean(),executed=g.executed.mean(),
                                     outside=g.outside_spent.mean(),unexecuted=g.abandoned_unexecuted.mean()))
    primary_df=pd.DataFrame(primary_rows);primary_df.to_csv(out/'primary_table.csv',index=False)
    matrix_rows=[dict(name=t['name'],kind=t['kind'],base=t['base'],completed=manifest['completed_by_cell'][t['name']],
                      config=json.dumps(t['config'],sort_keys=True),policy=json.dumps(t['policy'],sort_keys=True)) for t in plan['targets']]
    pd.DataFrame(matrix_rows).to_csv(out/'completed_matrix.csv',index=False)
    election_names=primary+['A_COMMIT','C_COMMIT','A_TIMECOMMIT','C_TIMECOMMIT','A_HOLDERS','C_HOLDERS','A_HHI','C_HHI','D_TIME']
    operating=data[(data.label=='plus_7d')&data.name.isin(election_names)].groupby('name').agg(
        correct_future_choice=('correct_future_choice','mean'),winner_undefined=('winner',lambda s:s.isna().mean()),
        organic_mean_events=('organic_events','mean'),creator_cash_change=('creator_pnl','mean'))
    operating.to_csv(out/'selection_and_participation.csv')
    unlock=data[(data.name.isin(['B','B_CREATOR','B_DESTROY','B_CREATOR_DESTROY']))&data.label.isin(['before_unlock','after_unlock'])].groupby(['name','label'])[['cohort_reserve','winner_reserve','support_claims','support_cash','support_unlock_proceeds']].mean().reset_index()
    unlock.to_csv(out/'unlock.csv',index=False)
    ordering=pd.read_csv(root/'pilot/ordering_search.csv')
    ordering_top=ordering[(ordering.fee_bps==40)&ordering.filled].sort_values('complete_exit_profit',ascending=False).head(4)
    gating=[]
    import xml.etree.ElementTree as ET
    for path in sorted(root.glob('gate*/tests.xml')):
        suites=list(ET.parse(path).getroot().iter('testsuite'))
        gating.append(dict(gate=path.parent.name,tests=sum(int(s.get('tests',0)) for s in suites),
                           failures=sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites)))
    gate_df=pd.DataFrame(gating);gate_df.to_csv(out/'test_gates.csv',index=False)
    completed_nonattack=sum(t['kind']=='no_attack' for t in plan['targets']);training=json.loads((root/'training_final/manifest.json').read_text())
    pilot=json.loads((root/'pilot/manifest.json').read_text())
    interrupted=json.loads((root/'training/manifest.json').read_text()).get('completed_exported_rows',0) if (root/'training/manifest.json').exists() else 0
    concise_pair=pf[(pf.name.isin(primary))&(pf.control=='A')&(pf.label=='plus_7d')&pf.metric.isin(['cohort_reserve','winner_depth_500','organic_active'])]
    positive=tf[(tf.low>0)&(tf.grid=='routing_only')]
    acceptance_statement=(f"In the migration-free routing grid, the smallest tested assumed propensity with a strictly positive lower interval for cohort retention is {positive.assumed_acceptance.min():.1f}. This is conditional on reach=.6 and the stated rejection behavior; it is not a universal threshold. The second grid includes migration=.25 and cannot attribute its effect solely to routing." if len(positive) else
                          'No migration-free routing propensity from 0 to 1 has a strictly positive lower 95% interval for seven-day cohort retained capital versus A under reach=.6 and the stated rejection behavior. There is no demonstrated break-even in that grid. The separate migration=.25 grid cannot attribute its effect solely to routing.')
    evidence=[]
    for name,control in [('B','A'),('C','A'),('D','A'),('D','INDEPENDENT_BATCH'),('D','SINGLE_BATCH')]:
        r=pf[(pf.name==name)&(pf.control==control)&(pf.label=='plus_7d')&(pf.metric=='cohort_reserve')].iloc[0]
        evidence.append(f"- {name} versus {control}: seven-day cohort reserve difference {r.mean_delta:+.3f}, 95% interval [{r.low:+.3f}, {r.high:+.3f}].")
    evidence_text='\n'.join(evidence)
    report=f'''# Narrative consolidation: completed bounded findings

This is an off-chain synthetic study. All behavioral parameters are assumptions;
no real-market validation, demand calibration, contracts, wallets or funds are
involved. The four earlier Phase 1 documents and all preexisting research are
preserved. Results below come from completed runs, not supported CLI flags.

## What actually ran

The study completed {completed_nonattack} distinct no-attack settings and
{len(plan['targets'])-completed_nonattack} trained-policy settings on **100 paired
confirmation seeds, 10000–10099**: **{manifest['completed_worlds']:,} worlds**,
each with 480 common latent opportunities, ten candidate identities, a 30-minute
primary election and seven days of follow-up. Operational close/delay stresses
are separately named. There were {manifest['failures']} confirmation exceptions.
Development used seeds 0–19 ({pilot['worlds']} pilot worlds); bounded policy search
used independent seeds 100–149 ({training['worlds']} worlds). These stages are not
pooled into the confirmation sample. The exact planned/completed cells, policy
parameters and seed counts are in `analysis/completed_matrix.csv` and the frozen
plan. This is not the full earlier factorial research program. The pre-confirmation
review also preserved {interrupted} exported rows from an interrupted initial
policy search; those rows are not used for final selection or confirmation.

| Mechanism | Implemented and executed |
| --- | --- |
| A | Ten funded independent curves; diagnostic election does not move purchases; cap, funded commitment overlays, holder and concentration comparisons |
| B | Half of protocol fees supports winner; separate authorized creator-fee 60/30/10 alternative; each has lock and literal-destruction variants, real costs and +72h unlock observations |
| C | Explicit mint authorization; reach, acceptance, rejection alternatives and voluntary net-proceeds migration; independently funded overlays and strategic policies |
| D | Uniform-price curve-batch from compatible conditional escrow; no prelaunch loser tokens; net/time-weighted commitments, lock willingness, authorization and refund stresses |
| Controls | Voluntary single-token spot, single-token batch, independent candidate batches with the same cash waiting, and spot holdings locked to close |

## Mechanical evidence and implementation limits

The high-precision reference reuses the original ledger at zero coupling; economic
runs use integer quote/claim settlement, never float permission to overspend.
Tests cover ownership, full/partial redemption, separate fees, aliases, consent,
atomic rollback, repeated claims/refunds, cancellation, expiry, no winner and
deterministic replay. Test artifacts include development failures as well as
passing gates:

{markdown(gate_df,['gate','tests','failures'])}

Arithmetic witnesses, distinct from Monte Carlo estimates: 1,000 claims have
reserve 60 and cap 110. Equal D subscribers paying 30 each receive 500 claims;
first exit pays 42.50 and leaves 17.50. A funded B purchase of 30 acquires
245.3624 claims; original holders can redeem about 84.5362 and leave only 5.4638
backing support inventory. The zero-fee ordering witness earns 100 on outlay 160.
Tight limits correctly refuse atomic conversions. Different fixed-budget paths
leave different claim-quantum dust with owners; exact world conservation still
holds. A failed initial dust assertion and a test-module namespace collision were
repaired only in new files and preserved in gate artifacts.

## Main observed outcomes

Quote values are abstract units; depth is gross privately executable sell proceeds
at 5% marginal impact. Organic activity counts funded actors in the trailing 1h,
6h and 24h windows at the respective checkpoints. Curves can retain a positive
quote while no one trades. A winner is diagnostic in A, so also inspect cohort
depth and the neutral candidate benchmark in raw results.

{markdown(primary_df,['name','checkpoint','cohort','winner','depth5','active','executed','outside','unexecuted'])}

Seven-day paired differences versus A, with seed-bootstrap 95% intervals:

{markdown(concise_pair,['name','metric','mean_delta','low','high'])}

The key retention comparisons, including matched batch controls, are:

{evidence_text}

The strongest favorable evidence is any positive absolute winner depth/retention
entry in these tables. The strongest contrary evidence is loss of whole-cohort
capital or activity, loss of an effect against the batch/lock controls, or gains
that disappear after support unlock. These quantities are shown together so an
increased winner share cannot substitute for a capital gain.

Election accuracy against the evaluator-only latent-offer benchmark (a limited
synthetic benchmark, not knowledge of genuine people) is:

{markdown(operating.reset_index(),['name','correct_future_choice','winner_undefined','organic_mean_events','creator_cash_change'])}

The primary variants have zero extra attention from winning. Positive and negative
attention sensitivities are separate cells, not evidence that an election creates
organic attention. All starting quote is 39,100 in each world, including the
funded attacker, unused capital and sponsor. No rejected budget regenerates cash.
Outside reserves remain accounted but are excluded from platform/cohort retention.

## Conditional acceptance and participation

{acceptance_statement}

{markdown(tf,['grid','assumed_acceptance','realized_quote_acceptance','capital_delta','low','high'])}

Assumed propensity is reduced by loyalty and price, so 1 does not mean universal
consent. Reach controls whether a loser-page order encounters the router at all.
`C_REACH_*`, `C_REJECT_*`, `C_MIGRATE_*`, `D_BROAD_*` and `D_LOCK_*` cells isolate
those assumptions. D's cash-lock willingness and allowed-winner choice are
different decisions from C's post-election consent. One-factor sweeps do not
establish a universal joint adoption threshold. All distributions and paired
differences, including no-benefit settings, are exported rather than selected
only for favorable averages.

## Unlocks, controls and interpretation

{markdown(unlock,['name','label','cohort_reserve','winner_reserve','support_claims','support_cash','support_unlock_proceeds'])}

B's purchased claims and actual fee cash have explicit owners. Locking is a
temporary restriction on selling; destruction leaves a separately reported
inaccessible buffer. Neither is permanent LP capital. The before/after-unlock
drop measures the withdrawal option that a locked snapshot conceals. Fee support
can pay earlier holders, as the exact witness demonstrates.

D is compared to independent batches and a voluntary single-token batch in the
paired table, holding the batch curve and pre-close cash waiting explicit. Any
gain against ten spot markets must survive those controls before it can be
attributed to narrative selection. Choosing a more popular candidate, restricting
available assets, batching entry prices and forcing cash to wait are distinct
causal changes. The controls do not identify a real-world equilibrium.

## Strategic attacks

Every macro policy has one 5,000-unit actor endowment across aliases. The bounded
search includes abstention, funded capture/dump sizes and exit times, wallet splits,
wash rounds, and predictable B-epoch frontruns. D searches funded commitments and
immediate/one-hour exits. Policies were optimized independently against A and the
other selected architectures; abstaining families create no duplicate confirmation
samples. Actor identities aggregate evaluation budgets only; public elections see
addresses. Fee/holder/concentration metrics can therefore be misleading.

{markdown(af,['name','mean_profit','low','high','profit_frequency','mean_peak','mean_fees','mean_other_trader_loss','complete_exits']) if len(af) else 'All macro search families selected abstention.'}

Profit frequency counts positive cash P&L with zero residual inventory. The full
table includes Wilson intervals, extrema, capital-days and a separately reported
10% annual opportunity-cost diagnostic. Peak recoverable funding is distinct from
irreversible fees. Other-trader losses are paired against the same mechanism
without that policy; a profitable trade also available in A is not automatically
a new consolidation exploit. A failure to find profit is only a finite search
result. Search spaces omit strategic borrowing, coalitions among unrelated actors,
creator-side bribes and general equilibrium entry.

Separately, the 56-cell known-order grid optimizes funded migration frontruns
against output limits and actual fee costs. Selected fee-bearing profitable cases:

{markdown(ordering_top,['slippage_bps','budget','peak_funding','irreversible_fees','complete_exit_profit','filled'])}

Identical known purchases in the A control produce the same ordering profit.
Routing and visible migrations concentrate opportunities; independent curves do
not remove same-token MEV. Tight zero-slippage cases refuse/roll back both
conversion legs, and the attacker still pays its own round trip. Primary D has no
prelaunch secondary winner market: such price manipulation is N/A before issuance;
its relevant attack is capital capture followed by first exit.

## Honest recommendation and plain English

**A: go as the research control.** It preserves asset choice and isolates the
costs and benefits of consolidation. This is not a recommendation to launch or
invest in memecoins. Its independent markets still have adverse selection and
ordering risk.

**B: no-go as a claimed durable liquidity innovation.** It recycles already paid
fees and changes who can sell into them. A larger winner position during a lock
does not establish improved cohort retention, private depth or organic survival.
The creator-fee variant also redirects losing creators' income; adoption is
unproven. It could be studied as an explicitly priced promotional expense, with
ownership/unlock disclosure and the measured costs accepted.

**C: conditional research only; no-go for an established superiority claim.**
It implements voluntary routing without confiscating loser reserves, but retention
depends on reach, actual acceptance, abandonment, prices and later selling.
Changing the token received creates no external capital. No universal acceptance
threshold or creator adoption estimate follows from these synthetic runs.

**D: no-go in this initial form without addressing allocation/exit incentives.**
Its batch allocation is mechanically funded, but equal average-price entry into
an increasing redeemable curve rewards the first seller at other subscribers'
expense. Cash waiting and concentration must be distinguished from better
organic demand. The adverse arithmetic and trained commitment/exit strategies
cannot be rescued by a high initial market cap.

In simple English: putting money behind one name can make that name look stronger.
It does not create more money or guarantee that buyers want it. Some buyers leave;
early holders can sell into the redirected purchases; batch subscribers can race
to withdraw before one another. The useful product hypothesis left open is better
discovery and voluntary execution, with costs and refusal visible—not a demonstrated
economic gain from electing a canonical coin.

## Reproduction and evidence

Run from the repository root using the existing environment. Choose a **new study
directory** for reruns and capture a new preservation inventory before starting.
The supplied completed bundle is `research/narrative_consolidation/bounded_study`.
First run `python -m bonding_lab.narrative init --root <new-study-directory>` to
capture the new preservation inventory. Reports are saved inside the study;
an existing top-level findings report is never overwritten by a reproduction.

```powershell
.\\.venv\\Scripts\\python.exe -m bonding_lab.narrative pilot --root <new-study-directory>
.\\.venv\\Scripts\\python.exe -m bonding_lab.narrative train --root <new-study-directory>
.\\.venv\\Scripts\\python.exe -m bonding_lab.narrative freeze --root <new-study-directory>
.\\.venv\\Scripts\\python.exe -m bonding_lab.narrative confirm --root <new-study-directory>
.\\.venv\\Scripts\\python.exe -m bonding_lab.narrative report --root <new-study-directory>
.\\.venv\\Scripts\\python.exe -m bonding_lab.narrative verify --root <study-directory>
```

The frozen plan hashes source and configurations before confirmation. Confirmation
stores all 100 common tapes, every seed/checkpoint result, representative complete
financial traces and terminal wallets for seed 10000 in every treatment, ranking
records, source snapshots, progress/failure records and completion manifests.
Other traces are reproducible with `python -m bonding_lab.narrative replay
--root <study-directory> --name C --seed 10037 --out <new-replay-directory>`;
replay verifies the exact stored outcome hash. They are not claimed already
exported. Bootstrap intervals describe seed variation
inside this model, not uncertainty about human behavior or real adoption. The
current API discovery snapshots from Phase 1 are not a calibration dataset.
'''
    (root/'NARRATIVE_RESEARCH_FINDINGS.md').write_text(report,encoding='utf-8')
    destination=Path('NARRATIVE_RESEARCH_FINDINGS.md')
    if not destination.exists():destination.write_text(report,encoding='utf-8')
    write_json(out/'manifest.json',dict(status='complete',rows=len(data),worlds=manifest['completed_worlds'],
               bootstrap_replications=2000,paired_seed_count=100,source_results_sha256=manifest['raw_results_sha256']))
    print('Wrote NARRATIVE_RESEARCH_FINDINGS.md and analysis tables',flush=True)
