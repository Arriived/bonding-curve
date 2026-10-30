from pathlib import Path
import sys,json,hashlib,gzip,zipfile,platform,importlib.metadata
from dataclasses import asdict
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'outputs/c_permissionless_study'
sys.path.insert(0,str(ROOT/'work/c_followup'))
from open_model import OpenWorld,Setting,Strategy,tape_for
from upstream.model import hash_obj

manifest=json.loads((BUNDLE/'confirmation_manifest.json').read_text())
assert manifest['status']=='complete' and manifest['worlds']==manifest['expected_worlds']==5600
plan=json.loads((BUNDLE/'plan.json').read_text())
frozen=json.loads((BUNDLE/'frozen.json').read_text())
effects=pd.read_csv(BUNDLE/'paired_effects.csv')
summaries=pd.read_csv(BUNDLE/'summaries.csv')
attacks=pd.read_csv(BUNDLE/'attacks.csv')
matched=pd.read_csv(BUNDLE/'matched_policy_effects.csv')
raw=pd.read_csv(BUNDLE/'confirmation.csv.gz')
assert len(raw)==22400 and raw.seed.nunique()==100
assert set(raw.label)=={'1h','24h','7d','exit'}
assert len(raw.groupby(['setting','arch','kind','seed']))==5600
assert (raw.groupby(['setting','arch','kind','seed']).size()==4).all()
assert raw[(raw.label=='exit')&(raw.kind!='idle')].attacker_residual.max()==0
preserved=json.loads((BUNDLE/'preservation.json').read_text())
assert preserved['status']=='passed' and preserved['changed_or_missing']==[]
for name in ('ledger.py','model.py','attacks.py'):
    assert (ROOT/'work/c_followup/upstream'/name).read_bytes()==(Path(r'C:\Users\moadl\OneDrive\Documents\ChatGPT\bonding curve research')/'bonding_lab/narrative'/name).read_bytes()

def effect(setting,metric='cohort_reserve',label='7d'):
    return effects[(effects.setting==setting)&(effects.metric==metric)&(effects.label==label)].iloc[0]
def summary(setting,arch,metric,label='7d',kind='idle'):
    return summaries[(summaries.setting==setting)&(summaries.arch==arch)&(summaries.metric==metric)&(summaries.label==label)&(summaries.kind==kind)].iloc[0]
def f(n):return f'{n:,.2f}'
def pct(row):return 100*row['delta']/row.A_mean if row.A_mean else float('nan')
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])

display=[('base','Free launch; routing only'),('spam10','10 additional spam mints'),('spam90','90 additional spam mints'),
         ('late90','90 late spam mints'),('low_reach','20% router reach'),('outside50','50% creator outside probability'),
         ('low_accept','Low acceptance ceiling'),('grouped90','90 spam; grouped incoming intentions'),('higher_trade_fee','1.25% underlying trading fees'),
         ('router_fee','Additional 0.45% router fee'),('daily_cap','Daily routing budget'),('expire6h','Six-hour expiry'),
         ('timecap','Time-weighted cap and minimum age'),('premium','Relative-price limit'),('combined','Combined safeguards'),('combined90','Combined safeguards with 90 spam')]
result_rows=[]
for key,label in display:
    r=effect(key)
    result_rows.append([label,f(r.A_mean),f(r.C_mean),f(r.delta),f'[{f(r.low)}, {f(r.high)}]',f'{pct(r):+.1f}%'])
attack_rows=[]
for _,r in attacks.iterrows():
    attack_rows.append([r.setting,r.arch,f(r.mean_profit),f(r.idle_profit),f(r.incremental_profit),f'[{f(r.low)}, {f(r.high)}]',f'{100*r.profit_frequency:.0f}%',f(r.peak)])
same_rows=[[r.setting,f(r.C_profit),f(r.A_same_policy_profit),f(r.delta),f'[{f(r.low)}, {f(r.high)}]'] for _,r in matched.iterrows()]

replays=[]
lookup={s['name']:s for s in plan['settings']}
for name,arch,kind,seed in [('base','C','idle',30037),('spam90','C','trained',30073),('combined90','C','trained',30042)]:
    p=Strategy()
    if kind=='trained':p=Strategy(**next(x['policy'] for x in frozen['selected'] if x['setting']==name and x['arch']==arch))
    s=Setting(**lookup[name]);w=OpenWorld(s,arch,tape_for(seed,s),p);rows=w.run()
    for row in rows:row.update(kind=kind,policy=hash_obj(asdict(p)))
    key=f'{name}:{arch}:{kind}:{seed}'
    actual=hash_obj(rows);expected=manifest['world_hashes'][key]
    assert actual==expected,key
    replays.append(dict(world=key,expected=expected,actual=actual,passed=True))
(BUNDLE/'replay_audit.json').write_text(json.dumps(dict(status='passed',worlds=replays),indent=2))

base=effect('base');guard=effect('combined');spam=effect('spam90')
baseline_depth=effect('base','winner_depth')
base_activity=effect('base','active')
text=f'''# C on an open launchpad: completed follow-up

30 October 2026. Synthetic, off-chain research. No deployment, wallet use, real funds, or empirical adoption calibration.

## Decision in plain English

Permissionless creation and optional consolidation can be separate layers. Anyone can create an independent coin; one narrative page gathers discovery, and a fresh buyer may explicitly choose its current lead. The platform cannot redirect third-party purchases or move existing holder collateral without authorization.

The fresh-seed base comparison changes seven-day whole-narrative backing from {f(base.A_mean)} in A to {f(base.C_mean)} in C: {f(base.delta)} ({pct(base):+.1f}%), with a 95% paired seed-bootstrap interval [{f(base.low)}, {f(base.high)}]. This is routing only: holder migration is disabled throughout this extension. It is a conditional model result, not a real-market forecast.

The safeguards and open-entry stresses below test both the possible benefit and the capture costs. Interpret attack profits against independently trained A and the same-policy A controls; ordinary early trading can also be profitable in A.

## What actually ran

- 21 matched environments, each with A and C: 4,200 no-active-trading-attack confirmation worlds.
- Eight independently selected policy targets: 800 trained-policy confirmation worlds.
- Six additional A controls receiving the exact frozen C policy: 600 worlds.
- Total: **5,600 confirmation worlds**, **100 fresh paired seeds 30000–30099**, and **22,400 checkpoint/terminal rows**.
- Development: 40 pilot worlds on seeds 2000–2004. Attack training: 3,200 worlds on separate seeds 200–219, using 20 candidate strategies per target. Development and training do not increase the confirmation sample size.
- All settings and the policy class were written before confirmation. Attack choices were frozen after training. Confirmation source hashes are enforced. There was no outcome-dependent early stopping or retuning.
- Eighteen new implementation tests passed. An expiry-boundary bug was found and corrected before predeclaration; the development record identifies it. The existing repository suite was not rerun because its code was copied read-only and never changed.
- Three arbitrary stored worlds replay with exact output hashes. Integer conservation and ownership assertions run at every observation and terminal checkpoint.

The primary prespecified contrast is base C versus matched A for seven-day backing. All other intervals are exploratory; there is no multiple-comparison-adjusted claim that every favorable cell will generalize. Sampling intervals omit uncertainty about real human behavior.

## Model and permissionless boundaries

The experiment uses an isolated copy of the previous integer independent-curve ledger, not modifications to the original repository. The curve remains a=.01 and b=.0001, quote quantum 10^-6, claim quantum 10^-4. It does not reproduce Pump's virtual-reserve formula or graduation into an AMM.

Every world has 39,100 quote units: 32,000 across 64 traders, 2,000 across ten original creators, 5,000 for the coordinated actor, and 100 for a sponsor. There are 480 common latent opportunities and the same original trader budgets across matched worlds. Extra mints create no additional money or opportunities. Sales and refunds reuse owned cash; no external replenishment occurs.

There is no platform launch fee in the base case and no mandatory creator purchase. Each launch incurs a synthetic .01 network payment and .02 account deposit, paid by the creator or attacker. The sponsorship sensitivity pays those costs from the same finite 100-unit sponsor. Deposits remain separately named cash accounts; no recoverability or token-market backing is assumed within the observation horizon. Cash P&L excludes them. These are abstract research costs, not current SOL conversions.

Ten original creators can launch externally in the outside-creator stress. Whole-narrative backing includes their markets, preventing an apparent gain from simply dropping refused creators from the denominator. Platform-only and all-market backing, including the separate outside alternative, are also exported. Fees earned by attacker-created mints are credited to the same real actor, including self-payments; they are not new capital.

The 10/90-spam settings have 20/100 total possible mints. The spam count is an exogenously declared stress; it is not an estimate of equilibrium launch supply. Creating more mints uses the actor's existing budget. Half the arrivals in the raw-feed stress receive equal per-live-mint discovery exposure; this is an explicit naive-feed assumption. The grouped-intentions setting removes that per-mint discovery lottery and preserves incoming preferences, without minting more demand. It does not validate a semantic classifier or prove a real grouped interface raises attention.

Late mints can launch and trade after close. They cannot reopen the fixed thirty-minute election. A fresh buyer can still explicitly choose the incumbent from a late entrant's native entry point. No existing position is converted. Multi-round leader changes, legitimate new entrants bringing fresh audiences, classifier false positives, and a creator participation equilibrium remain unimplemented.

The base acceptance ceiling is .6 and reach is .6. Loyalty and price reduce actual synthetic consent. Rejected buyers choose the preferred asset with probability .5, the outside alternative with probability .25, or retain cash otherwise. These are assumptions, not measured preferences. Directly choosing a mint and accepting a recommendation are different orders. Zero-reach and zero-acceptance-with-direct-fallback controls are covered by implementation tests.

The `active` count includes funded organic fills in any modeled market, including the outside alternative, over trailing 1h/6h/24h windows. It is not platform-only activity. Seven-day timestamps do not establish seven-day real-market survival.

## Retained backing at seven days

{table(['Environment','A backing','C backing','C−A','95% paired interval','Relative mean change'],result_rows)}

Relative changes are ratios of mean differences to mean A backing. Confidence intervals are in quote units. The curve shape is identical within every matched pair. All results are after normal scheduled sells and before forced diagnostic terminal exits.

In the base case, 5%-impact winner sell depth changes from {f(baseline_depth.A_mean)} to {f(baseline_depth.C_mean)}. Its paired difference is {f(baseline_depth.delta)} [{f(baseline_depth.low)}, {f(baseline_depth.high)}]. Funded active-trader count across all modeled markets changes from {f(base_activity.A_mean)} to {f(base_activity.C_mean)}. These measures answer different questions from whole-narrative backing.

## Strategic capture

Policies vary an actor-funded purchase budget of 250/1,000/3,000, purchase at 5%/85% of the contest window, and exit at finalization/one hour/six hours after finalization. Abstention and a 32-wallet split are included, for 20 candidates per target. The actor has 5,000 total across all aliases. In spam settings the same actor also pays launch costs and collects its mints' actual creator fees.

Training maximizes terminal cash P&L within this disclosed class; selected policies must fully exit token inventory in training. Both A and C are optimized separately for the base and 90-spam environments. Guarded C policies are also evaluated against A with the very same settings, size, timing, and exits. This is a bounded search, not a proof of a globally optimal attack.

{table(['Environment','Model','Total actor cash P&L','Idle actor P&L','Added P&L vs idle','95% interval for added P&L','Positive cash P&L','Peak deployed cash'],attack_rows)}

“Idle” in a spam environment means no active trading attack, but the exogenous spam launches still occur and can earn creator fees. Thus total actor profit alone is not the incremental benefit of a capture trade. The added-P&L column controls for that income and launch expense. All token-exit residuals are exported; an inaccessible account deposit is not counted as realized cash or a market reserve.

### Exact C-policy comparison against A

{table(['C environment','C actor P&L','A with identical policy','Additional P&L in C','95% paired interval'],same_rows)}

These are the appropriate within-policy comparisons for routing-amplified profit. An independently optimized A result remains a complementary check. Participant cash outcomes and attacker-induced trader losses are in `attacks.csv`; profit frequencies describe synthetic seeds, not the probability of an exploit on a real platform.

## Safeguards evaluated

- **Time-weighted cap:** integrate observable cap over the common pre-close window and require 300 seconds of age. Funding earlier remains allowed; the attacker is retrained.
- **Daily routing budget:** at most 25% of winner backing at close may be spent through recommendations per day. This is a whole-order limit; blocked orders fall back to the preferred mint without a failed-transaction cost. It is a flow limit, not an escrow fund. An attacker can increase the reference backing by purchasing before close.
- **Six-hour expiry:** after expiry, new orders return to ordinary direct choice. There is no forced sale or automatic re-election.
- **Relative-price limit:** offer the direct asset if the winner's marginal price exceeds 1.5 times the preferred asset's. Integer comparisons enforce this decision. It is meaningful only for this study's identical curve calibration, not arbitrary differently denominated real tokens.
- **Combined:** apply all four, including under 90 extra spam launches. Reducing attack returns by nearly disabling routing must not be confused with preserving the full economic benefit.

Extra 45-basis-point router fees apply only to routed purchases in their sensitivity and are paid from the same all-in budget. This is a generic execution-cost stress, not a replica of Pump's complete interface fee policy.

## Product implication

The concrete product is a shared narrative feed and an optional execution router over independent markets. A creator can launch without joining a fee pot. A coin page can offer the current lead while preserving direct purchase. Every purchase names the received mint and quote limits; a label change never changes old rights. External interfaces remain able to trade the original mint.

Pump's official documentation currently describes no platform creation fee, with network transaction costs and required account deposits still payable, and curve trading without a creator liquidity seed. That supports the launch-access analogy, not an assertion that Pump already implements this narrative mechanism. [Official fee page](https://pump.fun/docs/fees), [official program description](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md).

See `PERMISSIONLESS_C_PRODUCT_DESIGN.md` for entry flows, rights, late launches, costs, and incentives. The in-conversation concept contains illustrative coins and sends no orders.

## Evidence and reproduction

`c_permissionless_study/` contains the predeclared plan, frozen policies/source hashes, training/pilot/confirmation manifests, raw compressed runs, paired effects, summaries, attack and same-policy controls, representative traces, exact-hash replays, new test output, and repository preservation check. The bundle records {manifest['worlds']} completed confirmation worlds with no run exception.

To reproduce without overwriting this bundle, copy the supplied `source/c_followup` directory into `work/c_followup` under a new empty working directory. Use Python with numpy and pandas. Run the following in sequence, keeping the existing research folder read-only:

```text
python -B -m unittest discover -s work/c_followup -p test_open_model.py -v
python -B work/c_followup/run_study.py init
python -B work/c_followup/run_study.py pilot
python -B work/c_followup/run_study.py train
python -B work/c_followup/run_study.py confirm
python -B work/c_followup/run_study.py analyze
```

On another machine adjust only the repository path used for its read-only preservation inventory before initializing the new study; the new plan will capture that source change. Do not overwrite or pool the existing confirmation bundle. The saved original repository and the isolated upstream source copy remain byte-identical to their captured hashes.

## Limits on the decision

This study can falsify a particular synthetic routing design and quantify behavior within its assumed model. It cannot establish user willingness, honest creator entry, a production identity/grouping system, an equilibrium spam rate, bot competition, optimal ordering protection, Pump-equivalent markets, or production permissionlessness. A go decision for real deployment would require those additional kinds of evidence. A better discovery interface is a testable product hypothesis even if electing a permanent financial winner is not supported.
'''
(ROOT/'outputs/C_PERMISSIONLESS_FINDINGS.md').write_text(text,encoding='utf-8')
environment=dict(python=platform.python_version(),packages={x:importlib.metadata.version(x) for x in ('numpy','pandas')})
(BUNDLE/'environment.json').write_text(json.dumps(environment,indent=2))

source_dest=BUNDLE/'source/c_followup'
source_dest.mkdir(parents=True,exist_ok=True)
for p in (ROOT/'work/c_followup').rglob('*.py'):
    target=source_dest/p.relative_to(ROOT/'work/c_followup');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(p.read_bytes())
verification=dict(status='passed',confirmation_worlds=5600,confirmation_seeds=100,training_worlds=3200,pilot_worlds=40,new_tests=18,
                  exact_hash_replays=3,confirmation_exceptions=0,source_hashes=frozen['source_hashes'],
                  original_repository=json.loads((BUNDLE/'preservation.json').read_text()),
                  findings_sha256=hashlib.sha256((ROOT/'outputs/C_PERMISSIONLESS_FINDINGS.md').read_bytes()).hexdigest())
(BUNDLE/'final_validation.json').write_text(json.dumps(verification,indent=2))
with zipfile.ZipFile(ROOT/'outputs/C_PERMISSIONLESS_EVIDENCE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in BUNDLE.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(BUNDLE).as_posix())
    for name in ('C_PERMISSIONLESS_FINDINGS.md','PERMISSIONLESS_C_PRODUCT_DESIGN.md'):
        z.write(ROOT/'outputs'/name,name)
print('REPORT AND EVIDENCE READY')
print('BASE',base.to_dict())
print('COMBINED',guard.to_dict())
print('MATCHED POLICIES',matched.to_string(index=False))
