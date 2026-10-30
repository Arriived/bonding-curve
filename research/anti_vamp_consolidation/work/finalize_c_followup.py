from pathlib import Path
import sys,json,hashlib,zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/c_permissionless_study'
sys.path.insert(0,str(ROOT/'work/c_followup'))
from run_study import inventory,hashes

supp=json.loads((OUT/'lot_sensitivity/manifest.json').read_text())
assert supp['status']=='complete' and supp['worlds']==1200
assert hashes()==json.loads((OUT/'frozen.json').read_text())['source_hashes']
main=pd.read_csv(OUT/'paired_effects.csv')
lot=pd.read_csv(OUT/'lot_sensitivity/effects.csv')
attack=pd.read_csv(OUT/'lot_sensitivity/attacks.csv')
def fmt(x):return f'{x:,.2f}'
def mrow(name):return main[(main.setting==name)&(main.label=='7d')&(main.metric=='cohort_reserve')].iloc[0]
def lrow(name):return lot[(lot.setting==name)&(lot.metric=='cohort_reserve')].iloc[0]
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
rows=[]
for name in ('base','spam90','combined90'):
    a,b=mrow(name),lrow(name)
    rows.append([name,fmt(a.delta),fmt(b.A_mean),fmt(b.C_mean),fmt(b.delta),f'[{fmt(b.low)}, {fmt(b.high)}]'])
attack_rows=[[r.setting,fmt(r.C_profit),fmt(r.A_same_policy),fmt(r.added_profit),f'[{fmt(r.low)}, {fmt(r.high)}]'] for _,r in attack.iterrows()]

base,spam=lrow('base'),lrow('spam90')
if base.high<0:
    verdict='The basic routing benefit reverses under lot-based sales. The favorable primary base result is not robust to this holding-policy change.'
elif base.low<=0:
    verdict='The lot-based base comparison has no statistically resolved backing gain. The favorable primary base result is not robustly established across these selling rules.'
else:
    verdict='The base comparison still has a positive lower backing interval under lot-based sales, but its size remains conditional on the selling rule.'
if spam.low>0:
    spam_verdict='The 90-spam ranking also reverses: C has less backing in the primary whole-position policy and more under the lot policy. It would be misleading to claim that spam universally defeats routing from these results.'
elif spam.high<0:
    spam_verdict='C retains less backing than matched A in the 90-spam environment under both tested selling rules. That remains a model-conditional stress result.'
else:
    spam_verdict='The 90-spam difference is not statistically resolved under lot sales, despite being negative in the primary policy. The general spam conclusion is sensitive to the selling model.'

report=ROOT/'outputs/C_PERMISSIONLESS_FINDINGS.md'
old=report.read_text(encoding='utf-8')
(OUT/'primary_findings_before_lot_audit.md').write_text(old,encoding='utf-8')
decision=f'''\n**Updated assessment after the selling-policy audit:** {verdict} {spam_verdict} The tested capture policies remain a separate reason to withhold a launch recommendation. See the final appendix before interpreting the primary table.\n'''
old=old.replace('## Decision in plain English',decision+'\n## Decision in plain English',1)
appendix=f'''

## Additional sell-lot audit: 1,200 exploratory worlds

After primary confirmation, review identified another uncalibrated assumption: each scheduled sale in the primary model sells a fraction of the wallet's entire current position in that mint. Repeated purchases can therefore generate repeated whole-position sale events. Spreading acquisitions across many mints changes those interactions. This is an explicit behavioral policy, not a conservation error; it should not silently establish a general liquidity claim.

The additional audit sells a fraction of the quantity associated with the particular purchase that generated the sale intention. Independent lots remain separately owned; their sum must equal trader inventory before terminal liquidation. There is still no holder migration. The audit runs base, 90-spam, and combined-safeguard/90-spam environments using the same 100 tapes. Each has A/C without an active attack and the already frozen C policy in both A and C: 12 cells, 1,200 worlds, 4,800 observations. No policy is retrained. These are not 100 new independent seeds or replacement primary results.

{table(['Environment','Primary C−A','Lot A backing','Lot C backing','Lot C−A','95% lot paired interval'],rows)}

{verdict}

{spam_verdict}

The unchanged C policy produces the following terminal actor cash outcomes, with the exact same policy in A:

{table(['Environment','C actor cash P&L','Same policy in A','Extra P&L in C','95% paired interval'],attack_rows)}

These contrasts remain conditional on the assumed policy class and synthetic demand. Where a tested policy is profitable, it is a funded counterexample; where it is not, the absence of retraining is not evidence of safety. In spam environments the actor also receives its mints' creator fees, so total profit must be distinguished from trading-attack income.

The audit adds two deterministic smoke checks: an exit attached to one purchase cannot sell another purchase's quantity, and repeated runs reproduce the same observations. Lot ownership coverage and the original integer money/claim invariants are checked during every world. See `lot_sensitivity/plan.json`, `runs.csv.gz`, `effects.csv`, `attacks.csv`, and `manifest.json`. To reproduce after the main study, copy `source/lot_sensitivity.py` to `work/lot_sensitivity.py` in the new study directory and run `python -B work/lot_sensitivity.py` once.

The decision is **no-go for a claimed durable or manipulation-resistant winner-routing launchpad on this evidence**. A shared discovery page with transparent direct coin choice remains a product hypothesis. Further routing research should treat sale behavior, repeat purchases, direct fallback, real consent/reach, and creator entry jointly rather than choosing whichever holding rule produces the best backing chart. The visual concept illustrates rights and choices, not a validated safe mechanism.
'''
report.write_text(old+appendix,encoding='utf-8')

before=json.loads((OUT/'repository_before.json').read_text());after=inventory()
changed=[k for k,v in before.items() if after.get(k)!=v]
assert not changed,changed
preservation=dict(status='passed',files_checked=len(before),changed_or_missing=changed,added=sorted(set(after)-set(before)),repository_writes=False)
(OUT/'preservation.json').write_text(json.dumps(preservation,indent=2))
validation=json.loads((OUT/'final_validation.json').read_text())
validation.update(exploratory_lot_worlds=1200,lot_smoke_checks=2,lot_new_independent_seeds=False,
    original_repository=preservation,findings_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
    evidence_claim='5600 primary confirmation worlds plus 1200 exploratory selling-policy worlds; same 100 paired confirmation tapes')
(OUT/'final_validation.json').write_text(json.dumps(validation,indent=2))
with zipfile.ZipFile(ROOT/'outputs/C_PERMISSIONLESS_EVIDENCE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(OUT).as_posix())
    for name in ('C_PERMISSIONLESS_FINDINGS.md','PERMISSIONLESS_C_PRODUCT_DESIGN.md'):
        z.write(ROOT/'outputs'/name,name)
print(verdict);print(spam_verdict)
print(lot.to_string(index=False));print(attack.to_string(index=False))
print('FINAL PRESERVATION',len(before),'files unchanged')
