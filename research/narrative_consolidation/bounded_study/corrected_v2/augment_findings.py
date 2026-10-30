"""Reproducible human-readable interpretation and explicitly exploratory appendix."""
from pathlib import Path
import hashlib,json,sys
import pandas as pd

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[3]
sys.path.insert(0,str(WORKSPACE))
from bonding_lab.narrative.report import ci,markdown


def main():
    path=ROOT/'NARRATIVE_RESEARCH_FINDINGS.md';before=path.read_text(encoding='utf-8')
    body=before.split('\n<!-- supplemental-findings -->')[0]
    body=body.replace('The supplied completed bundle is `research/narrative_consolidation/bounded_study`.',
                      'The supplied completed bundle is `research/narrative_consolidation/bounded_study/corrected_v2`.')
    if '<!-- reviewed-summary -->' in body:
        start=body.index('<!-- reviewed-summary -->');end=body.index('<!-- end-reviewed-summary -->')+len('<!-- end-reviewed-summary -->')
        body=body[:start]+body[end:]
    primary=pd.read_csv(ROOT/'analysis/primary_table.csv')
    primary=primary[(primary.checkpoint=='plus_7d')&primary.name.isin(['A','B','B_CREATOR','C','D','SINGLE_BATCH','INDEPENDENT_BATCH'])]
    a=float(primary[primary.name=='A'].cohort.iloc[0]);c=float(primary[primary.name=='C'].cohort.iloc[0]);d=float(primary[primary.name=='D'].cohort.iloc[0])
    pairs=pd.read_csv(ROOT/'analysis/paired_differences.csv')
    captures=pd.read_csv(ROOT/'analysis/attack_confirmation.csv')
    frozen=json.loads((ROOT/'frozen_plan.json').read_text())
    cap=captures[captures.name=='ATTACK_C_capture'].iloc[0];dcap=captures[captures.name=='ATTACK_D_capture'].iloc[0]
    summary=f'''<!-- reviewed-summary -->
The central result is conditional, rather than a blanket rejection of consolidation.
Without attacks, C retained {c:.2f} versus A's {a:.2f} quote units at seven days
(+{(c/a-1)*100:.1f}%) and improved the selected winner's private depth. It also
had fewer active traders. A frozen C capture policy earned {cap.mean_profit:.2f}
after full exit (95% interval {cap.low:.2f}–{cap.high:.2f}); a D commitment/first-exit
policy earned {dcap.mean_profit:.2f} and profited in all 100 confirmation seeds.
D retained {d:.2f}, {(1-d/a)*100:.1f}% less than A, with no statistically resolved
retention advantage over the matched single-token batch. B's protocol-fee and
creator-fee support variants slightly reduced seven-day cohort backing.

The migration-free routing grid first has a positive lower capital interval at
assumed propensity .4, corresponding to **26.5% realized quote-weighted consent**
among reachable eligible orders. At .3 the capital interval includes zero.
That is a conditional grid result, not a universal adoption requirement or a
joint improvement in survival/activity. The full model/holding-policy uncertainty
below is larger than these seed intervals suggest.
<!-- end-reviewed-summary -->
'''
    insertion=body.index('## What actually ran')
    body=body[:insertion]+summary+'\n'+body[insertion:]
    original=pd.read_csv(ROOT/'confirmation/runs.csv.gz')
    alternative=pd.read_csv(ROOT/'exit_continuity_sensitivity/runs.csv.gz')
    base=original[(original.name=='A')&(original.label=='plus_7d')].set_index('seed').sort_index()
    changed=alternative[(alternative.name=='C')&(alternative.label=='plus_7d')].set_index('seed').sort_index()
    mean,lo,hi=ci(changed.cohort_reserve-base.cohort_reserve,'continuity-versus-A')
    profit=alternative[(alternative.name=='ATTACK_C_capture')&(alternative.label=='feasible_exit')].attacker_cash_pnl
    pm,pl,ph=ci(profit,'continuity-capture-profit')
    effects=pd.read_csv(ROOT/'exit_continuity_sensitivity/paired_effects.csv')
    revenue=[]
    for name in ('A','B','B_CREATOR','C','D'):
        g=original[(original.name==name)&(original.label=='feasible_exit')]
        revenue.append(dict(name=name,protocol_and_support_quote=(g.protocol_cash+g.platform_launch_cash+g.support_cash).mean(),
                            gross_protocol_fees=g.protocol_fees_accrued.mean(),gross_creator_fees=g.creator_fees_accrued.mean(),
                            trader_cash_change=g.trader_cash_change.mean(),creator_cash_change=g.creator_pnl.mean(),network_quote=g.network_cash.mean()))
    revenue=pd.DataFrame(revenue);revenue.to_csv(ROOT/'analysis/revenue_and_cash_outcomes.csv',index=False)
    appendix=f'''
<!-- supplemental-findings -->
## Additional holding-policy audit: exploratory, 200 worlds

The primary agent policy attaches sell intentions to the mint actually purchased.
After voluntary migration, an original loser-mint sell intention can therefore
become ineffective; winner inventory can be sold on later winner-mint intentions
or terminal exit. This is an uncalibrated holding-policy assumption, not a legal
lock or permanent LP capital. It can inflate the apparent persistence of migrated
backing. The migration-free acceptance grid avoids that particular channel.

An additional, explicitly exploratory check carries those existing sell intentions
forward to the received winner after conversion. It uses the same 100 tapes and
frozen economic settings for C without attack and with its already-trained capture
policy: 200 extra worlds, no retraining or replacement of the preregistered matrix.
It is model-sensitivity evidence, not another independent confirmation sample.

{markdown(effects,['name','metric','original_mean','continuity_mean','mean_delta','low','high'])}

Under sell-intent continuity, C's cohort gain versus A falls to {mean:.2f}
(95% paired interval [{lo:.2f}, {hi:.2f}]), from the primary gain of {c-a:.2f}.
The unchanged capture policy still earns {pm:.2f} on average after complete exit
(interval [{pl:.2f}, {ph:.2f}]). Thus the favorable capital result is sensitive
to agent holding rules, while profitable capture survives this alternative.
This materially limits a favorable interpretation of C's primary reserve result.

Reproduce the extra check and appendix, after generating the main report:

```powershell
.\\.venv\\Scripts\\python.exe research/narrative_consolidation/bounded_study/corrected_v2/migration_exit_sensitivity.py
.\\.venv\\Scripts\\python.exe research/narrative_consolidation/bounded_study/corrected_v2/augment_findings.py
```

The sensitivity script requires a new output directory if it has already run;
its saved `runs.csv.gz`, `paired_effects.csv` and manifest are the completed evidence.
All 196 main implementation tests pass; all 9,900 worlds outside the repaired
D refusal case match the preserved first run exactly. The earlier 10,000 worlds
are retained, not pooled to claim 200 independent confirmation seeds.

## Revenue and participant cash after feasible exits

{markdown(revenue,['name','protocol_and_support_quote','gross_protocol_fees','gross_creator_fees','trader_cash_change','creator_cash_change','network_quote'])}

Protocol/support cash includes launch receipts and cash remaining in the named
fund; gross fee accrual counts each actual trade, including support trades, and
is not additional external capital. Creator and trader cash changes use their
own funded initial balances. Network and outside-market accounts remain in world
conservation. Residual unprofitable-to-redeem claim dust is exported separately.
The table is a cash distribution, not a proof that fee revenue benefits traders.

There is favorable counterevidence to a blanket negative judgment: without an
attacker, D's mean trader cash loss is only {-float(revenue[revenue.name=='D'].trader_cash_change.iloc[0]):.2f}
versus A's {-float(revenue[revenue.name=='A'].trader_cash_change.iloc[0]):.2f}. B also
reduces trader cash losses modestly by transferring fee value away from its
other beneficiaries. These outcomes coexist with lower D trading/participation
and different creator cash outcomes; they are not proof of improved total welfare
or permanent liquidity. D's trained attack imposes roughly {dcap.mean_other_trader_loss:.2f}
additional trader loss relative to its no-attack world. No architecture is best
on every measured dimension under equal starting money.

## Decision and open questions

Retain A as the experimental control. Reject B as a demonstrated durable-liquidity
improvement and D's current allocation/exit design. C merits further controlled
research only: there is a measured conditional reserve/depth benefit, but lower
activity, profitable strategic capture and sensitivity to holding behavior prevent
a launch recommendation. Net commitment and time weighting both permit profitable
D capture; time weighting reduces the measured reward in this policy class but
does not establish a manipulation-resistant winner rule. Address concentration
penalties remain vulnerable to actor-controlled splits.

Losing C holders keep their original claims unless they authorize conversion;
D's incompatible subscribers refund. Creator adoption remains unknown: refusal
is an exogenous stress here, not an equilibrium participation estimate. The study
does not establish an added organic-attention effect, real human acceptance,
permanent liquidity, seven-day real-market survival, or a defensible moat.
Reject a broad production claim if it relies on ignoring abandonment, locked or
unclaimed money, the migration holding-policy effect, or attacks funded within
the tested 5,000-unit budget.
'''
    result=body.rstrip()+'\n'+appendix
    path.write_text(result,encoding='utf-8')
    top=WORKSPACE/'NARRATIVE_RESEARCH_FINDINGS.md'
    if not top.exists() or top.read_text(encoding='utf-8')==before:top.write_text(result,encoding='utf-8')
    metadata=dict(status='complete',main_worlds=10000,exploratory_worlds=200,independent_confirmation_seeds=100,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  main_frozen_plan_sha256=hashlib.sha256((ROOT/'frozen_plan.json').read_bytes()).hexdigest(),
                  final_findings_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (ROOT/'reviewed_findings_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'continuity_gain_vs_A':mean,'interval':[lo,hi],'continuity_capture_profit':pm,'profit_interval':[pl,ph]},indent=2))


if __name__=='__main__':main()
