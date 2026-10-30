from pathlib import Path
from dataclasses import asdict
import sys,json,hashlib,zipfile,os
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/anti_vamp_study'
sys.path.insert(0,str(ROOT/'work/anti_vamp'))
from model import Environment,Mechanism,Policy,World,make_tape,digest
from study import ci,hashes

plan=json.loads((OUT/'plan.json').read_text());frozen=json.loads((OUT/'frozen.json').read_text())
manifest=json.loads((OUT/'confirmation_manifest.json').read_text())
assert manifest['status']=='complete' and manifest['worlds']==manifest['expected']
assert hashes()==frozen['source_hashes']
d=pd.read_csv(OUT/'confirmation.csv.gz');s=pd.read_csv(OUT/'summaries.csv');ef=pd.read_csv(OUT/'paired_effects.csv')
tm=pd.read_csv(OUT/'time_to_concentration.csv');att=json.loads((OUT/'attack_results.json').read_text())
assert len(d)==manifest['worlds']*5
assert d.seed.nunique()==100
aliases=plan['aliases'];lookup={c['id']:c for c in plan['cells']}
def ident(alias):return aliases[alias]
def row(alias,label='15m'):
    return d[(d.cell==ident(alias))&(d.label==label)].sort_values('seed')
def mean(alias,metric,label='15m'):return float(row(alias,label)[metric].mean())
def summary(alias,metric,label='15m'):
    return s[(s.cell==ident(alias))&(s.metric==metric)&(s.label==label)].iloc[0]
def effect(alias,metric,label='15m'):
    return ef[(ef.cell==ident(alias))&(ef.metric==metric)&(ef.label==label)].iloc[0]
def fmt(x):return f'{x:,.2f}'
def pct(x):return f'{100*x:.1f}%'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v) for v in r)+' |' for r in rows])

core=[]
for n in (10,50,100):
    for mechanism in ('independent','original_first','elected_30s','elected_120s','elected_300s','elected_900s'):
        alias=f'copies{n-1}__{mechanism}';x=row(alias)
        core.append([n,mechanism,pct(x.original_share.mean()),pct(x.top_share.mean()),fmt(x.original_depth.mean()),
                     fmt(x.lead_depth.mean()) if mechanism!='independent' else 'N/A',pct(x.narrative_to_latent.mean())])
base=effect('copies9__original_first','original_share');depth=effect('copies9__original_first','original_depth')
lines=[]
for label in ('5m','15m','30m','60m'):
    for m in ('independent','original_first','elected_120s','elected_300s'):
        x=row('copies9__'+m,label)
        lines.append([label,m,pct(x.original_share.mean()),pct(x.top_share.mean()),fmt(x.original_depth.mean()),fmt(x.window_orders.mean())])
reach=[]
for r in (30,60,100):
    for a in (30,60,100):
        alias=f'reach{r}_accept{a}__original_first';x=row(alias)
        reach.append([f'{r}%',f'{a}%',pct(x.original_share.mean()),fmt(x.original_depth.mean()),
                      pct(x.authorized.sum()/x.reachable.sum()) if x.reachable.sum() else 'N/A'])
times=[]
for m in ('independent','original_first','elected_30s','elected_120s','elected_300s','elected_900s'):
    x=tm[tm.cell==ident('copies9__'+m)]
    times.append([m,pct(x.original50.le(15).mean()),pct(x.original70.le(15).mean()),pct(x.top70.le(15).mean()),
                  fmt(x.original50.dropna().median()) if x.original50.notna().any() else 'Not reached'])
attack_rows=[]
for r in att:
    attack_rows.append([r['cell'],r['family'],r['policy']['target'],r['policy']['budget'],fmt(r['actor_profit']),
        fmt(r['matched_A_profit']),fmt(r['extra_profit']),pct(r['actor_led_share']),
        f'[{fmt(r["low"])}, {fmt(r["high"])}]'])

# Exact replays of arbitrary post-freeze outcomes, not the seed used for saved traces.
targets=json.loads((OUT/'targets.json').read_text());replays=[]
for cell,seed in [('copies9__original_first',50037),('copies99__elected_120s',50073),('copy_attack__copies9__elected_120s',50042)]:
    target=next(t for t in targets if t['id']==cell);c=lookup[target['base']]
    e=Environment(**c['environment']);m=Mechanism(**c['mechanism'])
    w=World(e,m,make_tape(seed,e.opportunities,e.half_life),Policy(**target['policy']));obs,_=w.run()
    for x in obs:x.update(cell=target['id'],base=target['base'],kind=target['kind'])
    actual=digest(obs);expected=manifest['world_hashes'][f'{cell}:{seed}'];assert actual==expected
    replays.append(dict(cell=cell,seed=seed,hash=actual,passed=True))
(OUT/'replays.json').write_text(json.dumps(replays,indent=2))

nocopy=mean('no_copies__independent','original_depth')
preclaim=[]
for m in ('independent','original_first','elected_120s','elected_300s'):
    x=row('preclaimed__'+m)
    preclaim.append([m,pct(x.original_share.mean()),pct(x.lead_share.mean()) if x.lead_share.notna().any() else 'N/A',fmt(x.original_depth.mean())])
remaining=[]
for close in (30,120,300,900):
    fractions=[]
    for seed in plan['confirmation_seeds']:
        tape=make_tape(seed)
        fractions.append(sum(r['budget'] for r in tape['visits'] if r['t']>=close)/sum(r['budget'] for r in tape['visits']))
    remaining.append([f'{close/60:g} minutes',pct(sum(fractions)/len(fractions))])

report=f'''# Anti-vamp study: one original, many copies, first hour

30 October 2026. Completed synthetic test. The objective is early concentration of one meme's buying and usable liquidity, not seven-day survival.

## Primary result

With one original and nine copies, immediate original-first routing changes the original's share of executed narrative buying in the five-minute window ending at minute 15 from **{pct(base.A_mean)} to {pct(base.C_mean)}**. The paired difference is **{100*base.delta:.1f} percentage points**, with 95% interval [{100*base.low:.1f}, {100*base.high:.1f}].

Original-holder executable sell depth at 5% marginal impact changes from **{fmt(depth.A_mean)} to {fmt(depth.C_mean)} quote units** at the same checkpoint. The difference is {fmt(depth.delta)}, interval [{fmt(depth.low)}, {fmt(depth.high)}]. The no-copy reference's original depth is {fmt(nocopy)}. These are funded, instrument-specific execution measures, not market cap or newly created money.

The key interpretation is whether routing recovers concentration quickly, how much traffic/consent it requires, and whether an elected lead can be captured by a copy. A profitable early original-holder trade is not automatically a vampire exploit or a reason to reject this objective.

## What actually ran

- {len(plan['cells'])} unique no-active-attack economic cells × 100 fresh paired seeds: {len(plan['cells'])*100:,} worlds.
- Trained-strategy and exact-same-policy independent controls: {manifest['worlds']-len(plan['cells'])*100:,} additional worlds.
- **Total confirmation: {manifest['worlds']:,} worlds**, seeds 50000–50099. {manifest['checkpoints']:,} checkpoint/terminal rows and {manifest['minute_rows']:,} minute-flow rows.
- Development pilot: 90 worlds on seeds 3000–3004. Training: {json.loads((OUT/'training_manifest.json').read_text())['worlds']:,} worlds on distinct seeds 500–511. Training and repeated settings do not increase the 100-seed confirmation sample size.
- Nineteen implementation tests pass, including funding, consent, lot isolation, no-copy world funding, deterministic replay, an independent invariant check, no-winner fallback, and false first registration.
- Three arbitrary confirmation worlds replay exactly. The original repository remains read-only; preservation is checked separately.

The v1 development plan and pilot are preserved. Before training/confirmation, the design added a no-copy reference and explicit narrative fills, and used deterministic process parallelism. Before confirmation, copy-only strategies were selected separately from the already completed disclosed training grid. Both pre-confirmation versions are retained. No confirmation result was used to tune parameters or policies.

## The experiment

One true-original asset launches at time zero. Nine, 49, or 99 lookalikes follow, beginning after 15 seconds and normally all within three minutes. All refer to the same narrative. There are no ten unrelated fundamental demands or independent narrative endowments.

Each seed has the same 480 narrative visits, timestamps, users, and budget opportunities across matched worlds. Defaults are a ten-minute attention-arrival half-life within a one-hour horizon; 25% of post-copy landing intentions favor the original and 75% favor copies collectively. Copy intentions split uniformly unless a named viral-copy sensitivity gives one copy tenfold weight. More coins divide existing visits; they do not create more buyers or money.

World endowment is fixed at 39,100 quote: 32,000 across 64 traders, 2,000 across original/copy creators, 5,000 for a trading actor, and 100 sponsor cash. Platform launch fee and required creator buy are zero. Each creator funds .01 network cost and .02 account deposit. No free redeemable allocations exist. The no-copy control parks unused creator capital; its copy-creator cash metric is N/A, not an economic loss.

All markets use the earlier independently funded integer linear curve, with a=.01, b=.0001, quote quantum 10^-6 and claim quantum 10^-4. Default fees total .4%, including .3% creator fees; a 1.25% total-fee sensitivity is separate. This is not a replication of Pump's virtual reserves or graduation process. Each mint keeps its own reserve and creator fees. No loser principal is confiscated or migrated.

**Independent:** all buyers buy their intended mint.

**Original-first:** a fresh buyer at a participating copy entry point may authorize the first-registered mint instead. The first registration is fixed; it is not an identity oracle proving true authorship. In the default case the true original registers first. The false-first stress explicitly breaks that correspondence.

**Elected:** independent trading continues until a frozen market-cap selection after 30 seconds, two, five, or fifteen minutes. Only observations before close select the lead. After that, newly authorized orders may buy it. No eligible winner or a tie gives direct trading. An election can concentrate on a copy; that is distinct from protecting the original.

Default router reach and consent ceiling are both 60%. Loyalty modestly reduces realized consent. Buyers declining a recommendation buy their preferred mint in the primary experiment. Named sensitivities instead let them retain cash or buy an outside asset. Total narrative execution and top-flow capture of common latent budgets are recorded so abandonment cannot masquerade as successful concentration.

The primary holding rule sells only the acquisition lot associated with a planned sale. A whole-position sale sensitivity is separate. No winning-generated attention or external money is added. User acceptance, attention, copy arrivals, and holding behavior remain uncalibrated synthetic assumptions.

## Minute-15 concentration and depth

Shares are of executed narrative buy quote over minutes 10–15. Top share is the largest actual mint's share, whether original or copy. Original depth is constrained by organic holder inventory and actual backing. The selected lead's depth is separately compared with the same mint in the independent world in `paired_effects.csv`.

{table(['Coins','Mechanism','Original buy share','Largest buy share','Original depth','Selected depth','Narrative fills / latent budgets'],core)}

## How quickly concentration appears

{table(['Mechanism','Original ≥50% by 15m','Original ≥70% by 15m','Any coin ≥70% by 15m','Median time to original 50%, among hits'],times)}

The timing benchmark requires two consecutive minute observations of five-minute flow, at least five fills and 100 quote in each, and starts only after a full copy-exposure window. Non-reached cases are censored; the median among hits must not be read as the median across all worlds. Fifty/seventy percent are descriptive research benchmarks, not promises or empirically chosen adoption targets.

## Early versus delayed selection

{table(['Checkpoint','Mechanism','Original buy share','Largest buy share','Original depth','Mean fills in trailing 5m'],lines)}

Late low-volume intervals can have unstable shares; the early 5–15 minute checkpoints and minimum-volume timing tests are the main evidence. There is no requirement that activity or money survive indefinitely.

{table(['Election delay','Common latent buy budget still scheduled afterward'],remaining)}

These budget fractions quantify how much demand a fresh-order router can still affect under the primary hype curve. They are opportunities, not guaranteed funded fills or new deposits.

## Reach and willingness

{table(['Reach','Consent ceiling','Original share at 15m','Original depth','Realized reachable-order consent, quote weighted'],reach)}

With direct fallback and comparable fills, the accounting intuition is original share ≈ s+(1−s)×reach×actual consent. With original share s=.25, reaching .70 requires the product of reach and actual consent to be about .60. This is a mechanism constraint under the simplified split, not a measured real-user threshold. A shared group-buy button may reach a different self-selected audience than persuading people already intending a particular copy; that behavioral distinction is not calibrated here.

## Copy-led capture versus ordinary early-original trading

The policy grid includes abstention, targets original (0) or the first copy (1), budgets 500/2,000, fixed public start times, and exits at 5/15/30 minutes. Each actor has only its funded 5,000. The actor is a trader and does not receive creator fees; pooled creator control and arbitrary attacker programs are outside this search.

The overall profit-maximizing policy and the best copy-only policy are selected separately on training seeds, with abstention eligible. Exact same size/timing/target/exit policies are run against independent markets. Total profit alone is not an exploit finding: buying the original early is normal memecoin speculation. A funded copy winning the recommendation and receiving additional redirected demand is the contest-capture case.

{table(['Base cell','Policy family','Bought mint','Budget','Actor profit','Same policy A','Extra vs A','Selected mint equals bought mint at 15m','95% interval for extra'],attack_rows)}

For original-first with correct registration, buying a copy cannot replace the recipient. It can still be profitable to speculate on that independently traded copy. Likewise, stronger demand for the original can benefit its early holders without violating the anti-vamp goal. Inspect policy target and recipient, not just the profit column.

## First registration is not authenticity

This stress has a lookalike register one second before the true original. It is a conditional identity/coordination failure case, not an estimate of how often preclaiming occurs.

{table(['Mechanism','True-original buy share at 15m','Selected-lead buy share','True-original depth'],preclaim)}

An original-first product needs a clearly disclosed canonical mint and a way for buyers to judge that assignment. A name, ticker, semantic group, or first timestamp alone cannot prove authorship. Disputes cannot rewrite previously authorized assets or seize backing.

## Evidence and reproduction

The bundle contains the predeclared plan, both pre-confirmation revisions, frozen policies/source hashes, full primary and policy controls, minute flow, checkpoints, timing distributions, financial traces, raw training outcomes, tests, exact replays, and preservation inventory.

Copy `source/anti_vamp` to `work/anti_vamp` and `source/select_anti_vamp_copy_families.py` to `work/select_anti_vamp_copy_families.py` in a fresh directory. Run `python -B -m unittest discover -s work/anti_vamp -p test_model.py -v`. Then run `study.py init`, `pilot`, and `train` using `python -B work/anti_vamp/study.py <stage>`. Before confirmation, run `python -B work/select_anti_vamp_copy_families.py` to freeze the separate copy-only selections from the completed training grid. Finally run `study.py confirm` and `study.py analyze`. Do not overwrite this completed directory. No live chain, user accounts, or real funds are required.

Sampling intervals use paired seeds; wallets, minute observations, policy copies, and duplicate aliases are not additional independent samples. Most sensitivity comparisons are exploratory. The study evaluates liquidity concentration given assumed visits and consent; it does not measure human attention growth, grouping accuracy, platform adoption, creator equilibrium, or production security.
'''
(ROOT/'outputs/ANTI_VAMP_FINDINGS.md').write_text(report,encoding='utf-8')
src=OUT/'source/anti_vamp';src.mkdir(parents=True,exist_ok=True)
for p in (ROOT/'work/anti_vamp').glob('*.py'):(src/p.name).write_bytes(p.read_bytes())
(OUT/'source/select_anti_vamp_copy_families.py').write_bytes((ROOT/'work/select_anti_vamp_copy_families.py').read_bytes())

# Recheck the entire original durable-file inventory; no original files are written.
repo=Path(r'C:\Users\moadl\OneDrive\Documents\ChatGPT\bonding curve research')
before=json.loads((OUT/'repository_before.json').read_text());changed=[]
for rel,expected in before.items():
    path=repo/rel
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:changed.append(rel)
assert not changed
validation=dict(status='passed',confirmation_worlds=manifest['worlds'],paired_seeds=100,new_tests=19,replays=3,
    protected_original_files=len(before),changed_or_missing=changed,repository_writes=False,
    findings_sha256=hashlib.sha256((ROOT/'outputs/ANTI_VAMP_FINDINGS.md').read_bytes()).hexdigest(),
    data_dictionary='No-copy copy_creator_cash is N/A; unused creator allocation remains owned cash in a separate account.')
(OUT/'final_validation.json').write_text(json.dumps(validation,indent=2))
with zipfile.ZipFile(ROOT/'outputs/ANTI_VAMP_EVIDENCE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(OUT).as_posix())
    z.write(ROOT/'outputs/ANTI_VAMP_FINDINGS.md','ANTI_VAMP_FINDINGS.md')
print('PRIMARY SHARE',base.to_dict());print('PRIMARY DEPTH',depth.to_dict());print('NO COPY DEPTH',nocopy)
print('REACH',reach);print('TIMING',times);print('FALSE FIRST',preclaim)
print('PROTECTED',len(before),'original files unchanged')
