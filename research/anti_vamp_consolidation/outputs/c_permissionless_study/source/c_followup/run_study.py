"""Bounded predeclared follow-up; writes only inside this chat's outputs."""
from pathlib import Path
from dataclasses import asdict, replace
from datetime import datetime, timezone
import sys, os, json, gzip, csv, hashlib, time, shutil, traceback
import numpy as np
import pandas as pd
from open_model import Setting, Strategy, OpenWorld, tape_for
from upstream.model import Config, World, Policy, make_tape, hash_obj

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'outputs/c_permissionless_study'
REPO=Path(r'C:\Users\moadl\OneDrive\Documents\ChatGPT\bonding curve research')

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def now():return datetime.now(timezone.utc).isoformat()
def hashes():return {str(p.relative_to(HERE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.rglob('*.py'))}
def save(path,rows):
    if not rows:return
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'wt',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def inventory():
    result={};skip={'.git','.venv','__pycache__','.hypothesis','.pytest_cache','.tmp','shared_bonding_lab.egg-info'}
    for root,dirs,files in os.walk(REPO):
        dirs[:]=[d for d in dirs if d not in skip]
        for name in files:
            p=Path(root)/name
            if p.suffix=='.pyc':continue
            result[p.relative_to(REPO).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def settings():
    base=Setting()
    return [base,replace(base,name='spam10',spam=10),replace(base,name='spam90',spam=90),
        replace(base,name='late90',spam=90,late_spam=True),replace(base,name='low_reach',reach=.2),
        replace(base,name='outside50',outside_creators=.5),replace(base,name='low_accept',acceptance=.2),
        replace(base,name='reject_direct',reject_preferred=1,reject_outside=0),
        replace(base,name='grouped90',spam=90,feed_fraction=0),
        replace(base,name='higher_trade_fee',fp=95,fc=30),
        replace(base,name='sponsored90',spam=90,sponsor_launch=True),
        replace(base,name='priced90',spam=90,launch_fee=50_000_000),
        replace(base,name='zero_reach',reach=0),replace(base,name='zero_accept_direct',acceptance=0,reject_preferred=1,reject_outside=0),
        replace(base,name='daily_cap',route_cap=.25),replace(base,name='expire6h',route_hours=6),
        replace(base,name='timecap',rule='timecap',min_age=300),replace(base,name='premium',premium_limit=1.5),
        replace(base,name='combined',route_cap=.25,route_hours=6,rule='timecap',min_age=300,premium_limit=1.5),
        replace(base,name='combined90',spam=90,route_cap=.25,route_hours=6,rule='timecap',min_age=300,premium_limit=1.5),
        replace(base,name='router_fee',router_bps=45)]

def candidates():
    return [Strategy()]+[Strategy(b,start,hours) for b in (250,1000,3000) for start in (.05,.85) for hours in (0,1,6)]+[Strategy(3000,.85,1,32)]

TRAIN=[('base','A'),('base','C'),('spam90','A'),('spam90','C'),('daily_cap','C'),('timecap','C'),('combined','C'),('combined90','C')]

def initialize():
    p=OUT/'plan.json'
    if p.exists():raise RuntimeError('Plan already exists')
    OUT.mkdir(exist_ok=True,parents=True)
    write(OUT/'repository_before.json',inventory())
    write(p,dict(status='predeclared',created=now(),source_hashes=hashes(),settings=[asdict(s) for s in settings()],
                 train_targets=TRAIN,strategies=[asdict(s) for s in candidates()],development_seeds=list(range(2000,2005)),
                 training_seeds=list(range(200,220)),confirmation_seeds=list(range(30000,30100)),
                 confirmation_primary='base C versus matched A: 7d cohort backing; all other contrasts exploratory',
                 stopping_rule='all declared worlds, no optional stopping based on favorable results',
                 limits='Synthetic open-entry stress extension, not Pump formula replication, empirical calibration, or creator entry equilibrium'))
    print('PREDECLARED',len(settings()),'paired environments; original source inventory captured',flush=True)

def check_sources():
    plan=json.loads((OUT/'plan.json').read_text())
    if plan['source_hashes']!=hashes():raise RuntimeError('Source changed after predeclaration; preserve and version before rerunning')
    return plan

def pilot():
    plan=check_sources();rows=[];start=time.perf_counter()
    for seed in plan['development_seeds']:
        for s in (settings()[0],settings()[2],settings()[-2],settings()[-1]):
            for arch in ('A','C'):
                w=OpenWorld(s,arch,tape_for(seed,s));r=w.run()
                rows.append(r[-2])
    save(OUT/'pilot.csv',rows)
    write(OUT/'pilot_manifest.json',dict(status='complete',worlds=len(rows),elapsed=time.perf_counter()-start))
    print('PILOT',len(rows),'worlds',time.perf_counter()-start,flush=True)

def train():
    plan=check_sources();rows=[];selected=[];start=time.perf_counter();lookup={s.name:s for s in settings()}
    for name,arch in TRAIN:
        s=lookup[name];scores=[]
        for j,p in enumerate(candidates()):
            profits=[]
            for seed in plan['training_seeds']:
                w=OpenWorld(s,arch,tape_for(seed,s),p);last=w.run()[-1]
                assert last['attacker_residual']==0
                profits.append(last['attacker_profit'])
                rows.append(dict(setting=name,arch=arch,policy_id=j,seed=seed,profit=last['attacker_profit'],peak=last['attacker_peak']))
            scores.append(float(np.mean(profits)))
        best=max(range(len(scores)),key=lambda j:(scores[j],-j))
        selected.append(dict(setting=name,arch=arch,policy=asdict(candidates()[best]),training_mean=scores[best],idle_mean=scores[0]))
        save(OUT/'training.csv.gz',rows);write(OUT/'selected.json',selected)
        print('TRAINED',name,arch,'best',selected[-1],flush=True)
    write(OUT/'training_manifest.json',dict(status='complete',worlds=len(rows),elapsed=time.perf_counter()-start))
    write(OUT/'frozen.json',dict(status='frozen_before_confirmation',created=now(),source_hashes=hashes(),plan_hash=hash_obj(plan),selected=selected))
    print('FROZEN',len(rows),'training worlds',flush=True)

def confirm():
    plan=check_sources();frozen=json.loads((OUT/'frozen.json').read_text())
    if frozen['source_hashes']!=hashes():raise RuntimeError('Frozen source mismatch')
    result=OUT/'confirmation.csv.gz'
    if result.exists():raise RuntimeError('Confirmation output already exists')
    lookup={s.name:s for s in settings()};worlds=0;start=time.perf_counter();world_hashes={};tapes={};failures=[]
    matched=[x for x in frozen['selected'] if x['arch']=='C']
    manifest=dict(status='running',worlds=0,expected_worlds=100*(len(settings())*2+len(TRAIN)+len(matched)),failures=[],started=now())
    with gzip.open(result,'wt',newline='',encoding='utf-8') as f:
        writer=None
        for seed in plan['confirmation_seeds']:
            targets=[(s,arch,'idle',Strategy()) for s in settings() for arch in ('A','C')]
            targets += [(lookup[x['setting']],x['arch'],'trained',Strategy(**x['policy'])) for x in frozen['selected']]
            targets += [(lookup[x['setting']],'A','matched_C_policy',Strategy(**x['policy'])) for x in matched]
            for s,arch,kind,p in targets:
                tape=tape_for(seed,s);tapes[f'{s.name}:{seed}']=tape['_sha256']
                capture=seed==30000 and s.name in ('base','spam90','combined90')
                w=OpenWorld(s,arch,tape,p,capture=capture)
                try: observations=w.run()
                except Exception:
                    write(OUT/'failure.json',dict(setting=asdict(s),arch=arch,kind=kind,seed=seed,traceback=traceback.format_exc()))
                    raise
                for row in observations:row.update(kind=kind,policy=hash_obj(asdict(p)))
                key=f'{s.name}:{arch}:{kind}:{seed}'
                world_hashes[key]=hash_obj(observations)
                if writer is None:writer=csv.DictWriter(f,fieldnames=list(observations[0]));writer.writeheader()
                writer.writerows(observations);worlds+=1
                if capture:
                    trace=OUT/'traces';trace.mkdir(exist_ok=True)
                    with gzip.open(trace/f'{s.name}_{arch}_{kind}_{seed}.json.gz','wt',encoding='utf-8') as z:
                        json.dump(dict(events=w.b.trace,observations=observations),z,separators=(',',':'))
            if (seed-29999)%10==0:
                f.flush();manifest.update(worlds=worlds,elapsed=time.perf_counter()-start)
                write(OUT/'confirmation_manifest.json',manifest)
                print('CONFIRM',seed-29999,'/100;',worlds,'worlds;',round(time.perf_counter()-start,1),'sec',flush=True)
    manifest.update(status='complete',worlds=worlds,elapsed=time.perf_counter()-start,finished=now(),
                    seed_count=100,source_hashes=hashes(),world_hashes=world_hashes,tape_hashes=tapes)
    write(OUT/'confirmation_manifest.json',manifest)

def ci(a,key):
    a=np.asarray(a,dtype=float);rng=np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big'))
    boots=a[rng.integers(0,len(a),(2000,len(a)))].mean(axis=1)
    return float(a.mean()),float(np.quantile(boots,.025)),float(np.quantile(boots,.975))

def analyze():
    check_sources();df=pd.read_csv(OUT/'confirmation.csv.gz');effects=[];summaries=[]
    for (setting,arch,kind,label),g in df.groupby(['setting','arch','kind','label']):
        for metric in ('cohort_reserve','platform_reserve','all_market_reserve','winner_depth','active','events','trader_cash','creator_cash','attacker_profit','attacker_peak','routed','actual_consent','launched','captured'):
            vals=g[metric].dropna()
            if len(vals):
                mean,lo,hi=ci(vals,f'summary:{setting}:{arch}:{kind}:{label}:{metric}')
                summaries.append(dict(setting=setting,arch=arch,kind=kind,label=label,metric=metric,mean=mean,low=lo,high=hi))
    for s in settings():
        for label in ('1h','24h','7d','exit'):
            a=df[(df.setting==s.name)&(df.arch=='A')&(df.kind=='idle')&(df.label==label)].set_index('seed').sort_index()
            c=df[(df.setting==s.name)&(df.arch=='C')&(df.kind=='idle')&(df.label==label)].set_index('seed').sort_index()
            for metric in ('cohort_reserve','platform_reserve','all_market_reserve','winner_depth','active','events','trader_cash','creator_cash'):
                mean,lo,hi=ci(c[metric]-a[metric],f'paired:{s.name}:{label}:{metric}')
                effects.append(dict(setting=s.name,label=label,metric=metric,A_mean=float(a[metric].mean()),C_mean=float(c[metric].mean()),delta=mean,low=lo,high=hi))
    attacks=[]
    for name,arch in TRAIN:
        x=df[(df.setting==name)&(df.arch==arch)&(df.kind=='trained')&(df.label=='exit')].set_index('seed').sort_index()
        b=df[(df.setting==name)&(df.arch==arch)&(df.kind=='idle')&(df.label=='exit')].set_index('seed').sort_index()
        mean,lo,hi=ci(x.attacker_profit-b.attacker_profit,f'attack:{name}:{arch}')
        attacks.append(dict(setting=name,arch=arch,mean_profit=float(x.attacker_profit.mean()),idle_profit=float(b.attacker_profit.mean()),incremental_profit=mean,low=lo,high=hi,
                            profit_frequency=float((x.attacker_profit>0).mean()),incremental_frequency=float((x.attacker_profit>b.attacker_profit).mean()),peak=float(x.attacker_peak.mean()),residual=float(x.attacker_residual.max()),
                            other_trader_loss=float((b.trader_cash-x.trader_cash).mean())))
    save(OUT/'paired_effects.csv',effects);save(OUT/'summaries.csv',summaries);save(OUT/'attacks.csv',attacks)
    matched_effects=[]
    for name,arch in TRAIN:
        if arch!='C':continue
        c=df[(df.setting==name)&(df.arch=='C')&(df.kind=='trained')&(df.label=='exit')].set_index('seed').sort_index()
        a=df[(df.setting==name)&(df.arch=='A')&(df.kind=='matched_C_policy')&(df.label=='exit')].set_index('seed').sort_index()
        mean,lo,hi=ci(c.attacker_profit-a.attacker_profit,f'matched-policy:{name}')
        matched_effects.append(dict(setting=name,C_profit=float(c.attacker_profit.mean()),A_same_policy_profit=float(a.attacker_profit.mean()),delta=mean,low=lo,high=hi))
    save(OUT/'matched_policy_effects.csv',matched_effects)
    print(pd.DataFrame(effects).query("label=='7d' and metric in ['cohort_reserve','active']").to_string(index=False),flush=True)
    print(pd.DataFrame(attacks).to_string(index=False),flush=True)
    before=json.loads((OUT/'repository_before.json').read_text());after=inventory()
    changed=[k for k in before if before[k]!=after.get(k)]
    write(OUT/'preservation.json',dict(status='passed' if not changed else 'failed',files_checked=len(before),changed_or_missing=changed,
                                    added=sorted(set(after)-set(before)),checked=now(),repository_writes=False))

if __name__=='__main__':
    stage=sys.argv[1]
    {'init':initialize,'pilot':pilot,'train':train,'confirm':confirm,'analyze':analyze}[stage]()
