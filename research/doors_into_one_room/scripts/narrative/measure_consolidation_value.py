"""Measure consolidation accounting from the existing real launch/account snapshots.

Offline, deterministic, no semantic labels or simulated agents. Completed groups
are baseline successes only. Current reserves provide conservative accounting
opportunities under fixed grouping/cashflows, not causal shared-market outcomes.
"""
import csv
import datetime
from decimal import Decimal,ROUND_CEILING
import hashlib
import json
import math
import re
import sys

import calibrate_text as T
import matcher as M
from audit_liveness_brief import OUT,ROOT
from collect_consolidation_balances import OUTPUT,SCHEMA,decode_pool,jobs,pool_addresses
from collect_consolidation_outcomes import DATA,decode
from liveness_reads import bonding_curve

sys.path.insert(0,str(ROOT/'scripts'))
from account_sizes import graduation_rent_lamports
from curve_identities import R_STAR,LAMPORTS


def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def quantile(values,p):
    values=sorted(values)
    if not values:return None
    at=(len(values)-1)*p
    low=math.floor(at);high=math.ceil(at)
    return values[low]+(values[high]-values[low])*(at-low)


def distribution(groups):
    positive=[g for g in groups if g['sum_lamports']>0]
    money=sum(g['sum_lamports'] for g in positive)
    fragments=sum(g['nonlargest_lamports'] for g in positive)
    values=[g['copy_money_share'] for g in positive]
    return {'groups':len(groups),'positive_reserve_groups':len(positive),'zero_reserve_groups':len(groups)-len(positive),
        'reserve_lamports':money,'nonlargest_lamports':fragments,
        'weighted_mean':fragments/money if money else None,
        **{name:quantile(values,p) for name,p in [('p25',.25),('median',.5),('p75',.75),('p90',.9)]}}


def load_groups():
    original=[json.loads(l) for l in DATA.read_text(encoding='utf-8').splitlines()]
    run=json.loads((OUT/'consolidation_collection.json').read_text(encoding='utf-8'))
    balance_run=json.loads((OUT/'consolidation_balance_collection.json').read_text(encoding='utf-8'))
    source=json.loads(SCHEMA.read_text(encoding='utf-8'))
    assert run['complete'] and balance_run['complete']
    assert balance_run['source_outcomes_sha256']==hashlib.sha256(DATA.read_bytes()).hexdigest()
    launch_hash=hashlib.sha256((OUT/'pump_launches.jsonl').read_bytes()).hexdigest()
    assert run['source_launch_sha256']==launch_hash
    assert all(r['source_launch_sha256']==launch_hash for r in original)
    launches=T.load(OUT/'pump_launches.jsonl')
    by_mint={r['mint']:r for r in launches}
    assert len(original)==len(launches) and {r['mint'] for r in original}==set(by_mint)
    for record in original:
        assert all(record[k]==v for k,v in decode(record['account']).items())
    records=[json.loads(l) for l in OUTPUT.read_text(encoding='utf-8').splitlines()]
    by_root={r['root_mint']:r for r in records}
    expected=jobs()
    assert len(by_root)==len(records)==len(expected)
    groups=[]
    for job in expected:
        r=by_root[job['root_mint']]
        assert {m['mint'] for m in r['members']}=={m['mint'] for m in job['members']}
        members=[]
        root=by_mint[r['root_mint']]
        for m in r['members']:
            launch=by_mint[m['mint']]
            curve=decode(r['accounts'][bonding_curve(m['mint'])])
            assert curve==m['curve'] and curve['sol_quoted']
            reserve=curve['real_quote_reserves_raw']
            pool={}
            if curve['complete']:
                pool_key,vault_key=pool_addresses(m['mint'])
                pool=decode_pool(r['accounts'][pool_key],r['accounts'][vault_key],m['mint'],source)
                assert pool==m['pool'] and pool['real_pool_quote_lamports'] is not None
                reserve+=pool['real_pool_quote_lamports']
            assert reserve==m['real_sol_reserve_lamports'] and reserve>=0
            members.append({'mint':m['mint'],'launch_slot':launch['slot'],'launch_time':launch['block_time'],
                'complete':curve['complete'],'curve_reserve_lamports':curve['real_quote_reserves_raw'],
                'pool_reserve_lamports':pool.get('real_pool_quote_lamports',0),
                'real_sol_reserve_lamports':reserve,
                'pool_protocol_fees':pool.get('protocol_fees_lamports',0),
                'pool_creator_fees':pool.get('creator_fees_lamports',0),
                'pool_boost_quote_lamports':pool.get('boost_quote_lamports',0),
                'root_age_at_launch_seconds':launch['block_time']-root['block_time']})
        total=sum(m['real_sol_reserve_lamports'] for m in members)
        largest=max(m['real_sol_reserve_lamports'] for m in members)
        prefix=[m for m in members if m['root_age_at_launch_seconds']<M.DEFAULTS['live_new_seconds']]
        groups.append({'root_mint':r['root_mint'],'name':root['name'],'symbol':root['symbol'],
            'root_launch_time':root['block_time'],'context_slot':r['context_slot'],
            'received_at_utc':r['received_at_utc'],'members':members,'member_count':len(members),
            'any_completed':any(m['complete'] for m in members),
            'completed_members':sum(m['complete'] for m in members),
            'sum_lamports':total,'max_lamports':largest,'nonlargest_lamports':total-largest,
            'copy_money_share':(total-largest)/total if total else None,
            'grace_prefix_members':len(prefix),'grace_prefix_sum_lamports':sum(m['real_sol_reserve_lamports'] for m in prefix),
            'expired_grace_copies_unknown':len(members)-len(prefix)})
    return groups,original,launches


def ks_distance(values,cdf):
    values=sorted(values);n=len(values);best=0;i=0
    while i<n:
        j=i+1
        while j<n and values[j]==values[i]:j+=1
        model=cdf(values[i])
        best=max(best,abs(i/n-model),abs(j/n-model))
        i=j
    return best


def fit_tail(lamports,minimum_tail=50):
    values=sorted(v/1e9 for v in lamports if v>0)
    candidates=[]
    for xmin in sorted(set(values)):
        tail=[x for x in values if x>=xmin]
        if len(tail)<minimum_tail:break
        logs=sum(math.log(x/xmin) for x in tail)
        if logs<=0:continue
        alpha=len(tail)/logs  # survival exponent; density exponent is alpha+1
        d=ks_distance(tail,lambda x:1-(xmin/x)**alpha)
        ll=len(tail)*math.log(alpha/xmin)-(alpha+1)*logs
        excess=sum(x-xmin for x in tail)
        rate=len(tail)/excess if excess else None
        exp_ll=len(tail)*math.log(rate)-rate*excess if rate else None
        candidates.append({'xmin_sol':xmin,'xmax_sol':tail[-1],'n_tail':len(tail),
            'alpha_survival':alpha,'density_exponent':alpha+1,'ks_distance':d,
            'unbounded_model_mean_is_finite':alpha>1,
            'tail_dynamic_range':tail[-1]/xmin,'pareto_conditional_log_likelihood':ll,
            'pareto_aic':2-2*ll,'exponential_rate':rate,
            'exponential_ks':ks_distance(tail,lambda x:1-math.exp(-rate*(x-xmin))) if rate else None,
            'exponential_aic':2-2*exp_ll if exp_ll is not None else None})
    if not candidates:return {'fit':None,'reason':'too few nonzero groups for the declared minimum tail size'}
    best=min(candidates,key=lambda c:(c['ks_distance'],-c['n_tail']))
    if best['exponential_aic'] is not None and best['exponential_aic']<best['pareto_aic']:
        verdict='The shifted exponential has better conditional AIC on this same tail; an unbounded Pareto is not preferred.'
    elif best['ks_distance']<=.1 and best['n_tail']>=50 and best['tail_dynamic_range']>=10:
        verdict='A Pareto is a serviceable descriptive fit over the selected observed tail, not a validated population law.'
    else:
        verdict='The selected tail does not establish a persuasive unbounded power law; inspect its KS distance, size and range.'
    fixed=[]
    for p in (.5,.75,.9):
        xmin=quantile(values,p);tail=[x for x in values if x>=xmin]
        logs=sum(math.log(x/xmin) for x in tail)
        fixed.append({'positive_maxima_quantile':p,'xmin_sol':xmin,'n_tail':len(tail),
                      'alpha_survival':len(tail)/logs if logs else None})
    return {'fit':best,'minimum_tail_size':minimum_tail,'positive_groups':len(values),
        'selected_by':'minimum descriptive KS over observed positive cutoffs; ties prefer larger tail',
        'verdict':verdict,'cutoff_sensitivity':fixed,
        'no_calibrated_p_value':'alpha and xmin are selected on the same data; no simulated/bootstrap goodness-of-fit p-value is claimed'}


def threshold_counts(groups,threshold):
    eligible=[g for g in groups if not g['any_completed']]
    base=sum(g['max_lamports']>=threshold for g in eligible)
    pooled=sum(g['sum_lamports']>=threshold for g in eligible)
    new=[g for g in eligible if g['sum_lamports']>=threshold and g['max_lamports']<threshold]
    prefix=[g for g in eligible if g['grace_prefix_sum_lamports']>=threshold and g['max_lamports']<threshold]
    return {'threshold_lamports':threshold,'uncompleted_groups':len(eligible),
        'separate_current_max_above':base,'current_sum_above':pooled,'additional_candidates':len(new),
        'additional_candidate_roots':[g['root_mint'] for g in new],
        'in_window_grace_prefix_candidates':len(prefix),
        'counted_multiplier':pooled/base if base else None}


def money_threshold(price,usd):
    return int((Decimal(usd)*Decimal(10**9)/price).to_integral_value(rounding=ROUND_CEILING))


def percentage(value):
    return 'undefined' if value is None else f'{value:.2%}'


def render(report):
    pooled=report['distributions']['all_groups_both_statuses']
    copies=report['distributions']['copy_clusters_both_statuses']
    head=report['thresholds'][0]
    sources=report['sources']
    price=sources['sol_usd']['response']['data']['amount']
    names={'all_groups_both_statuses':'All groups, both completion classes',
        'copy_clusters_both_statuses':'Copy clusters, both completion classes',
        'all_groups_completed_member':'Groups with a completed member',
        'all_groups_no_completed_member':'Groups with no completed member',
        'copy_clusters_completed_member':'Copy clusters with a completed member',
        'copy_clusters_no_completed_member':'Copy clusters with no completed member',
        'all_groups_below_money_cut':'All groups below money cut',
        'all_groups_at_or_above_money_cut':'All groups at/above money cut',
        'copy_clusters_below_money_cut':'Copy clusters below money cut',
        'copy_clusters_at_or_above_money_cut':'Copy clusters at/above money cut',
        'no_completed_member':'Groups with no completed member'}
    infinite_mean=[names[name] for name,fit in report['tail_fits'].items()
                   if fit['fit'] and fit['fit']['alpha_survival']<=1]
    mean_note=('The fitted survival exponents at or below one ('+', '.join(infinite_mean)+
        ') imply no finite mean for the ideal unbounded Pareto. Actual capital is finite. '
        'Together with observed concentration, this is another reason not to extrapolate '
        'the finite-window weighted c as a universal input.' if infinite_mean else
        'The fitted unbounded Pareto means are finite, but the data remain a selected finite-window snapshot.')
    lines=['<!-- generated by scripts/narrative/measure_consolidation_value.py -->',
        '# Consolidation value: current-reserve accounting', '',
        f"**Snapshot headline: {head['additional_candidates']} additional narratives clear the "
        f"spec’s {head['threshold_lamports']/1e9:.9f} SOL trigger by pooling current reserves.** "
        f"Reserve-weighted copy-money share c is **{percentage(pooled['weighted_mean'])} across all "
        f"SOL text groups**, including singletons, and **{percentage(copies['weighted_mean'])} among "
        'multi-member copy clusters**. Both figures include completed and uncompleted groups.', '',
        'This is a conservative snapshot accounting result under fixed cashflows and grouping, '
        'not an estimate that lifetime consolidation gain is zero. Current reserves cannot exceed '
        'a cluster’s historical aggregate peak. Past higher reserves could add candidates; how many '
        'is unmeasured and the historical count may equal the bound. Actual production graduation '
        'is also affected by the liveness gate and shared-market behaviour, so this is not an '
        'unconditional lower bound on real product outcomes.', '',
        f"The {report['completed_groups']} groups with a completed member already produced a "
        f"fragmented-market completion and contribute **no additional graduation**. The "
        f"{report['uncompleted_groups']} groups with no completed member are the headline population. "
        'The former group enters measured c only; no larger-room or incremental-graduation claim '
        'is made from its pooled balances.', '',
        '## Corrections applied', '',
        'A completed curve’s zero reserve is not a failed launch or lost outcome: completion '
        'is the baseline success flag, and verified pool reserve restores its money for c. '
        'Waiting pool fees and virtual boost are excluded. Uncompleted does not imply the '
        'production liveness gate passes. The full quote mix replaces the earlier subsample '
        'approximation; no non-SOL reserve is treated as lamports. The conservative count may '
        'equal its historical counterpart; “strictly higher” is not established.', '',
        '## Cohort and measurements', '',
        f"The original {report['launches']} launches span {report['window_hours']:.2f} hours. "
        f"Every curve was read: {report['sol_launches']} SOL quotes retained; "
        f"{report['non_sol_launches']} other quotes ({report['non_sol_launches']/report['launches']:.2%}) "
        f"excluded, with no mixed-asset conversion. Exact v1 folded-identity/name equality forms "
        f"{report['groups']} groups, including {copies['groups']} multi-member clusters. "
        'No URI, social, image, symbol-only, fuzzy or assistant-semantic labels alter grouping.', '',
        f"Initial curve reads: finalized slots {report['initial_slot_range'][0]}–{report['initial_slot_range'][1]}. "
        f"Refined balances: slots {report['balance_slot_range'][0]}–{report['balance_slot_range'][1]}, "
        f"{report['balance_time_range'][0]} to {report['balance_time_range'][1]}. All accounts within "
        'each group share one RPC context; different groups use sequential snapshots.', '',
        f"All {report['verified_pool_members']} completed SOL members have verified canonical pools. "
        'Member reserve means the curve’s real SOL reserve plus migrated real WSOL pool reserve. '
        'For pools, real reserve is vault token amount minus waiting protocol/creator fees; virtual '
        f"boost is excluded. Waiting fees excluded total {report['pool_fees_excluded_lamports']/1e9:.9f} SOL. "
        'Raw curve, pool and vault bytes, owners, timestamps and slots are cached. '
        f"See the [official fee/reserve identity]({report['pool_fee_source_url']}).", '',
        f"USD is a fixed normalisation at **${price}/SOL**, Coinbase observation "
        f"{sources['sol_usd']['fetched_at_utc']} ([source]({sources['sol_usd']['source_url']})). "
        'It is not a historical USD valuation or a market-cap threshold. The spec trigger is '
        'derived from its curve default plus graduation rent and checked against §2; it remains '
        'a Config value copied into each Room, not a new hardcoded program constant.', '',
        '## Threshold counts: only groups with no completed member', '',
        '| reserve threshold | SOL | USD at stated price | largest member above | combined above | additional candidates | grace-prefix candidates |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in report['thresholds']:
        lines.append(f"| {r['label']} | {r['threshold_lamports']/1e9:.6f} | ${r['usd_value']:,.2f} | "
            f"{r['separate_current_max_above']} | {r['current_sum_above']} | {r['additional_candidates']} | "
            f"{r['in_window_grace_prefix_candidates']} |")
    lines += ['', f"Largest current combined reserve among uncompleted groups is "
        f"{report['maximum_uncompleted_sum_lamports']/1e9:.9f} SOL "
        f"(${report['maximum_uncompleted_sum_lamports']/1e9*float(price):,.2f}). "
        'Completed groups are excluded at every cut, not added back as hypothetical extra graduates. '
        'For every group the per-member maximum and sum are in `consolidation_clusters.csv` and JSON. '
        'Within this observed cohort, a gate-induced split cannot exceed the all-live group sum; '
        'the zero current-candidate result therefore cannot increase from splitting alone. '
        'Unobserved pre-window members remain a separate limitation.', '',
        '## Copy-money share c', '',
        '`c = (sum of member reserves − largest member reserve) / sum of member reserves`. '
        'The pooled weighted mean is Σ(nonlargest reserve)/Σ(total reserve), not an average '
        'of group percentages. Zero-total groups have undefined c and are excluded from '
        'percentiles; their zero weight does not change the weighted mean. This is a current '
        'reserve-stock share, including migrated liquidity, not a measured lifetime gross-spending '
        'split; buying, selling, fees and liquidity changes can alter it.', '',
        '| population | groups / positive | reserve SOL | p25 | median | p75 | p90 | reserve-weighted mean |',
        '|---|---:|---:|---|---|---|---|---|']
    for name,d in report['distributions'].items():
        lines.append(f"| {names[name]} | {d['groups']} / {d['positive_reserve_groups']} | {d['reserve_lamports']/1e9:,.6f} | "
            f"{percentage(d['p25'])} | {percentage(d['median'])} | {percentage(d['p75'])} | "
            f"{percentage(d['p90'])} | {percentage(d['weighted_mean'])} |")
    lines += ['', f"The money split is ${report['money_split_usd']:,} of total current cluster "
        'reserve, using the same fixed price. It distinguishes funded narratives from dust, '
        'and includes both completion classes. Copy-only rows avoid a median dominated by '
        'singletons; all-group rows represent the whole observed SOL population.', '',
        f"Concentration matters: {report['concentration']['top_group_share_of_nonlargest']:.2%} "
        'of off-largest reserve sits in one already-completed text group. Its root mint is '
        f"`{report['concentration']['top_group_root']}`. This is an observed concentration, "
        'not a reason to remove the group or relabel it; it limits extrapolation from this window.', '',
        '## Tail fit and predicted versus counted multipliers', '',
        'Fit the **survival exponent** α in P(M≥x) ∝ x^−α, where M is each group’s largest '
        'member reserve, so the unit is the same narrative counted in the threshold table. '
        'The density exponent is α+1. Continuous Pareto MLE chooses xmin by minimum descriptive '
        'KS with a declared minimum tail size. A shifted exponential is fitted to the same '
        'selected tail for a conditional AIC comparison.', '',
        '| population | xmin SOL | xmax SOL | tail n | α | Pareto KS | exponential KS | Pareto AIC | exponential AIC |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,value in report['tail_fits'].items():
        f=value['fit']
        if f:
            lines.append(f"| {names[name]} | {f['xmin_sol']:.6g} | {f['xmax_sol']:.6g} | {f['n_tail']} | "
                f"{f['alpha_survival']:.6f} | {f['ks_distance']:.6f} | {f['exponential_ks']:.6f} | "
                f"{f['pareto_aic']:.3f} | {f['exponential_aic']:.3f} |")
    for name,value in report['tail_fits'].items():
        lines += ['', f"**{names[name]}:** {value.get('verdict',value.get('reason'))}"]
    lines += ['', 'These are in-sample descriptive fits, not calibrated goodness-of-fit tests. '
        'Cutoff and α are chosen on the same observations; no simulated/bootstrap p-value is '
        'claimed. The cutoff is selected for the Pareto, so the conditional AIC comparison '
        'is not an independent family-selection test. The no-completion cohort is selected against high historical reserves and '
        'is truncated by completion/migration, making unbounded extrapolation particularly weak. '
        'Cutoff-sensitivity fits and sample ranges are in the JSON report.', '',
        mean_note, '',
        f"The formula (1−c)^−α gives {report['predictions']['pooled_both_classes_multiplier']:.6f}× "
        'using the whole-population c and tail, but that population includes already completed '
        'narratives. For the eligible no-completion cohort, its own c and tail give '
        f"{report['predictions']['eligible_same_cohort_multiplier']:.6f}×. "
        'Only the latter is a like-population comparison for the headline. Neither is evidence '
        'of larger post-graduation rooms. A constant c, an untruncated power-law tail, and stable '
        'group composition are assumptions of that formula; the observed c varies by group.', '',
        '| diagnostic threshold USD | SOL | largest above | sum above | new candidates | counted multiplier | same-cohort formula | inside selected observed tail? |',
        '|---|---:|---:|---:|---:|---:|---:|---|']
    for r in report['diagnostic_thresholds']:
        multiplier='undefined' if r['counted_multiplier'] is None else f"{r['counted_multiplier']:.6f}×"
        lines.append(f"| ${r['usd_value']:,.2f} | {r['threshold_lamports']/1e9:.6f} | "
            f"{r['separate_current_max_above']} | {r['current_sum_above']} | {r['additional_candidates']} | "
            f"{multiplier} | {report['predictions']['eligible_same_cohort_multiplier']:.6f}× | {r['inside_fitted_tail']} |")
    lines += ['', 'The required graduation/high-dollar cuts have no eligible largest-member or '
        'pooled exceedances, so their counted multiplier is undefined, not one. Lower diagnostic '
        'cuts are shown to expose the counting comparison; they do not stand for a narrative '
        'that caught on. Where a scalar formula differs from the finite counts, the counts win. '
        'Variable c, cohort selection, a selected/censored tail and discrete small counts explain '
        'why the formula need not reproduce them. This does not validate a universal multiplier.', '',
        '## Limits', '',
        f"- **Gate coverage:** {report['gate_coverage']['copies_within_in_window_grace']} of "
        f"{report['gate_coverage']['copy_routes']} conditional text-copy joins are within the "
        f"configured grace; {report['gate_coverage']['expired_grace_unknown']} need missing "
        'historical reserve, idle, volume or pool-checkpoint state. Current account reads cannot '
        'substitute for launch-time histories. Uncompleted is not the same as gate-live. Main groups use exact v1 text equality with an '
        'explicit all-live accounting assumption; the grace-prefix column uses only the '
        'in-window root’s protected prefix. No production-gated point estimate is claimed.',
        '- **Pre-window roots:** the true truncated-root count is unknown. Every observed root '
        'lies in this sample by construction; that is not evidence that no earlier matching '
        'room existed. Grace diagnostics condition on an empty in-window replay boundary.',
        f"- **Age:** member reserves were read at {report['read_age_hours']['minimum']:.3f}–"
        f"{report['read_age_hours']['maximum']:.3f} hours after launch (median "
        f"{report['read_age_hours']['median']:.3f}). No invented fixed-age or linear age correction "
        'is applied. Older launches had more time to both attract buying and experience selling; '
        'the raw snapshot is not a launch-age-controlled comparison.',
        '- **Window:** one short contiguous, Halloween-season sample cannot establish long-run '
        'fragmentation, rare narratives or lifetime economic value. No semantic labels are '
        'invented: these are operational text groups, not independently adjudicated narratives.',
        '- **Counterfactual:** the accounting assumes the same buyers spend the same amounts, '
        'with member cashflows/withdrawals and grouping held fixed. A shared curve changes '
        'slippage, selling, routing, fees and incentives, which this measurement cannot capture.',
        '- **Reaching versus holding:** the earlier simulation in `DESIGN.md` found shared curves '
        'could drain faster when holders take profit together. It is not new measurement here. '
        'This study counts current accounting threshold opportunities, not how long a shared '
        'room would hold them or how large an already graduated room would become.', '',
        '## Reproduce', '', '```bash',
        'python3 scripts/narrative/collect_consolidation_outcomes.py --collect',
        'python3 scripts/narrative/collect_consolidation_balances.py --collect',
        'python3 scripts/narrative/measure_consolidation_value.py', '```', '',
        'Collectors resume their cached run without replacing completed observations. The '
        'measurement command is offline and uses only the standard library. Source hashes, '
        'complete per-group/member data and fit details are in `outputs/narrative/consolidation_value.json`; '
        'the CSV lists every group’s maximum, sum, completion class and c.']
    text='\n'.join(lines)+'\n'
    (OUT/'consolidation_value.md').write_text(text,encoding='utf-8',newline='\n')
    (ROOT/'CONSOLIDATION_VALUE.md').write_text(text,encoding='utf-8',newline='\n')


def main():
    groups,original,launches=load_groups()
    sources=json.loads((OUT/'consolidation_sources.json').read_text(encoding='utf-8'))
    price=Decimal(sources['sol_usd']['response']['data']['amount'])
    trigger=int(R_STAR*LAMPORTS)+graduation_rent_lamports()
    spec=(ROOT/'PERMANENT_CURVE_SPEC.md').read_text(encoding='utf-8')
    recorded=int(re.search(r'\| trigger T = R\* \+ rent \| ([\d,]+) lamports',spec)[1].replace(',',''))
    assert trigger==recorded
    no_completion=[g for g in groups if not g['any_completed']]
    copy_groups=[g for g in groups if g['member_count']>1]
    money_split=10000
    split_lamports=money_threshold(price,money_split)
    distributions={
        'all_groups_both_statuses':distribution(groups),
        'copy_clusters_both_statuses':distribution(copy_groups),
        'all_groups_completed_member':distribution([g for g in groups if g['any_completed']]),
        'all_groups_no_completed_member':distribution(no_completion),
        'copy_clusters_completed_member':distribution([g for g in copy_groups if g['any_completed']]),
        'copy_clusters_no_completed_member':distribution([g for g in copy_groups if not g['any_completed']]),
        'all_groups_below_money_cut':distribution([g for g in groups if g['sum_lamports']<split_lamports]),
        'all_groups_at_or_above_money_cut':distribution([g for g in groups if g['sum_lamports']>=split_lamports]),
        'copy_clusters_below_money_cut':distribution([g for g in copy_groups if g['sum_lamports']<split_lamports]),
        'copy_clusters_at_or_above_money_cut':distribution([g for g in copy_groups if g['sum_lamports']>=split_lamports])}
    thresholds=[]
    for label,cut in [('spec default',trigger)]+[(f'${v:,}',money_threshold(price,v)) for v in (10000,50000,100000)]:
        thresholds.append({'label':label,**threshold_counts(groups,cut),'usd_value':float(Decimal(cut)*price/Decimal(10**9))})
    fits={'all_groups_both_statuses':fit_tail([g['max_lamports'] for g in groups]),
          'no_completed_member':fit_tail([g['max_lamports'] for g in no_completion])}
    predictions={}
    for label,population,fitname in [('pooled_both_classes',groups,'all_groups_both_statuses'),
                                      ('eligible_same_cohort',no_completion,'no_completed_member')]:
        c=distribution(population)['weighted_mean'];alpha=fits[fitname]['fit']['alpha_survival']
        predictions[label+'_multiplier']=(1-c)**(-alpha)
        predictions[label+'_c']=c;predictions[label+'_alpha']=alpha
    diagnostics=[]
    f=fits['no_completed_member']['fit'];c=predictions['eligible_same_cohort_c']
    for usd in (10,100,1000):
        cut=money_threshold(price,usd)
        diagnostics.append({**threshold_counts(groups,cut),'usd_value':float(Decimal(cut)*price/Decimal(10**9)),
            'inside_fitted_tail':f['xmin_sol']<=cut/1e9*(1-c) and cut/1e9<=f['xmax_sol']})
    read_ages=[(datetime.datetime.fromisoformat(g['received_at_utc']).timestamp()-m['launch_time'])/3600 for g in groups for m in g['members']]
    pool_sources=json.loads(SCHEMA.read_text(encoding='utf-8'))
    largest_fragment=max(groups,key=lambda g:g['nonlargest_lamports'])
    report={'scope':'owner-approved current-reserve accounting; completed groups excluded from extra-graduation gain',
        'reserve_units':'native SOL in lamports; other quotes retained as raw quote-token base units and excluded from monetary sums',
        'launches':len(launches),'sol_launches':sum(len(g['members']) for g in groups),
        'non_sol_launches':sum(r.get('sol_quoted') is False for r in original),
        'window_hours':(max(r['block_time'] for r in launches)-min(r['block_time'] for r in launches))/3600,
        'groups':len(groups),'completed_groups':sum(g['any_completed'] for g in groups),
        'uncompleted_groups':len(no_completion),'verified_pool_members':sum(g['completed_members'] for g in groups),
        'initial_slot_range':[min(r['context_slot'] for r in original),max(r['context_slot'] for r in original)],
        'balance_slot_range':[min(g['context_slot'] for g in groups),max(g['context_slot'] for g in groups)],
        'balance_time_range':[min(g['received_at_utc'] for g in groups),max(g['received_at_utc'] for g in groups)],
        'maximum_uncompleted_sum_lamports':max(g['sum_lamports'] for g in no_completion),
        'pool_fees_excluded_lamports':sum(m['pool_protocol_fees']+m['pool_creator_fees'] for g in groups for m in g['members']),
        'pool_fee_source_url':next(iter(pool_sources['official_fee_definition_sources'])),
        'sources':sources,'money_split_usd':money_split,'distributions':distributions,
        'concentration':{'top_group_root':largest_fragment['root_mint'],
            'top_group_share_of_nonlargest':largest_fragment['nonlargest_lamports']/sum(g['nonlargest_lamports'] for g in groups)},
        'thresholds':thresholds,'diagnostic_thresholds':diagnostics,'tail_fits':fits,'predictions':predictions,
        'read_age_hours':{'minimum':min(read_ages),'maximum':max(read_ages),'median':quantile(read_ages,.5)},
        'gate_coverage':{'copy_routes':sum(g['member_count']-1 for g in groups),
            'copies_within_in_window_grace':sum(g['grace_prefix_members']-1 for g in groups),
            'expired_grace_unknown':sum(g['expired_grace_copies_unknown'] for g in groups),
            'full_production_replay_available':False},
        'prewindow_truncated_roots':None,'semantic_labels_used':False,
        'historical_peak_additional_count':None,'causal_consolidation_graduation_count':None,
        'groups_data':groups,
        'input_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [OUT/'pump_launches.jsonl',DATA,OUTPUT,SCHEMA,OUT/'consolidation_sources.json']}}
    dump(OUT/'consolidation_value.json',report)
    fields=['root_mint','name','symbol','member_count','any_completed','completed_members','context_slot',
        'sum_lamports','max_lamports','nonlargest_lamports','copy_money_share',
        'grace_prefix_members','grace_prefix_sum_lamports','expired_grace_copies_unknown']
    with (OUT/'consolidation_clusters.csv').open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
        writer.writeheader();writer.writerows(groups)
    render(report)
    print(json.dumps({'additional_candidates':thresholds[0]['additional_candidates'],
        'completed_groups':report['completed_groups'],'c_all':distributions['all_groups_both_statuses']['weighted_mean'],
        'c_copy':distributions['copy_clusters_both_statuses']['weighted_mean'],
        'tail_fits':fits,'predictions':predictions},indent=2))


if __name__=='__main__':main()
