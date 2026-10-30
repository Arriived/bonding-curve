from pathlib import Path
from dataclasses import asdict,replace
from datetime import datetime,timezone
import sys,json,hashlib,time,gzip,csv,platform
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from model import Environment,Mechanism,Policy,World,make_tape,digest

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'outputs/anti_vamp_study'

def now():return datetime.now(timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def hashes():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}
def save(p,rows):
    if not rows:return
    opener=gzip.open if str(p).endswith('.gz') else open
    with opener(p,'wt',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def ci(a,key):
    a=np.asarray(a,dtype=float);a=a[np.isfinite(a)]
    if not len(a):return None,None,None
    r=np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big'))
    b=a[r.integers(0,len(a),(2000,len(a)))].mean(axis=1)
    return float(a.mean()),float(np.quantile(b,.025)),float(np.quantile(b,.975))

def design():
    A=Mechanism();O=Mechanism('original_first','original')
    elections=[Mechanism(f'elected_{s}s','cap',s) for s in (30,120,300,900)]
    cells=[];aliases={};seen={}
    def add(e,m):
        econ=asdict(e);econ.pop('name')
        if m.rule=='independent':econ.update(reach=0,acceptance=0,rejection='direct')
        mech=asdict(m);mech.pop('name')
        key=digest([econ,mech]);alias=f'{e.name}__{m.name}'
        if key not in seen:
            cell=dict(id=alias,environment=asdict(e),mechanism=asdict(m),economic_key=key)
            seen[key]=alias;cells.append(cell)
        aliases[alias]=seen[key]
    for n in (10,50,100):
        e=Environment(name=f'copies{n-1}',coins=n)
        for m in [A,O]+elections:add(e,m)
    for reach in (.3,.6,1.):
        for accept in (.3,.6,1.):
            e=Environment(name=f'reach{int(reach*100)}_accept{int(accept*100)}',reach=reach,acceptance=accept)
            for m in (A,O,elections[1]):add(e,m)
    for n in (10,100):
        base=Environment(name=f'copies{n-1}',coins=n)
        variants=[replace(base,name=f'fast{n}',half_life=120),replace(base,name=f'slow{n}',half_life=1200),
                  replace(base,name=f'viral{n}',viral_copy=True),replace(base,name=f'position_sales{n}',sale_rule='position')]
        for e in variants:
            for m in (A,O,elections[1],elections[2]):add(e,m)
    for share in (.1,.5):
        e=Environment(name=f'original_share{int(share*100)}',original_share=share)
        for m in (A,O,elections[1]):add(e,m)
    for delay in (120,600):
        e=Environment(name=f'copies_after{delay}s',first_copy=delay)
        for m in (A,O,elections[1],elections[2]):add(e,m)
    for e in [Environment(name='preclaimed',preclaim=True),Environment(name='reject_leave',rejection='leave'),
              Environment(name='reject_outside',rejection='outside'),Environment(name='fees125',fee_bps=125)]:
        for m in (A,O,elections[1],elections[2]):add(e,m)
    add(Environment(name='no_copies',coins=1),A)
    # Every C setting explicitly points to its own matched independent environment.
    for c in list(cells):
        if c['mechanism']['rule']!='independent':add(Environment(**c['environment']),A)
    for c in cells:
        c['control']=aliases[f'{c["environment"]["name"]}__independent']
    return cells,aliases

def policies():
    return [Policy()]+[Policy(target,start,budget,end) for target,start in ((0,1),(1,16),(1,119),(1,299)) for budget in (500,2000) for end in (300,900,1800)]

TRAIN_ALIASES=['copies9__independent','copies9__original_first','copies9__elected_120s',
               'copies9__elected_300s','copies99__original_first','copies99__elected_120s']

def init():
    if (OUT/'plan.json').exists():raise RuntimeError('Plan exists')
    cells,aliases=design()
    write(OUT/'plan.json',dict(status='predeclared',created=now(),source_hashes=hashes(),cells=cells,aliases=aliases,
        training=TRAIN_ALIASES,policies=[asdict(p) for p in policies()],development_seeds=list(range(3000,3005)),
        training_seeds=list(range(500,512)),confirmation_seeds=list(range(50000,50100)),
        primary='One original + nine copies: original-first minus independent original buying share and organic 5%-impact sell depth at 15 minutes',
        goals='Reduce short-window fragmentation; report true-original and any-leader concentration separately; no longevity endpoint',
        benchmarks='50% and 70% 5-minute buying share, sustained for two minute observations, >=5 fills and 100 quote; start after a full copy-exposure window',
        attention='Fixed common narrative visits and budgets; no winning-generated demand or empirical attention claim',
        limitations='Synthetic willingness, copy arrival and holding policies; one-hour linear-curve model, not Pump replication'))
    print('PREDECLARED',len(cells),'unique cells;',len(aliases),'requested aliases;',len(cells)*100,'main worlds',flush=True)

def plan():
    p=json.loads((OUT/'plan.json').read_text())
    assert p['source_hashes']==hashes(),'source changed after predeclaration'
    return p

def pilot():
    p=plan();rows=[];start=time.perf_counter()
    for seed in p['development_seeds']:
        for cell in p['cells'][:18]:
            e=Environment(**cell['environment']);m=Mechanism(**cell['mechanism'])
            w=World(e,m,make_tape(seed,e.opportunities,e.half_life));obs,_=w.run()
            rows.append(dict(cell=cell['id'],seed=seed,original_share=obs[1]['original_share'],original_depth=obs[1]['original_depth']))
    save(OUT/'pilot.csv',rows)
    write(OUT/'pilot_manifest.json',dict(status='complete',worlds=len(rows),elapsed=time.perf_counter()-start))
    print('PILOT',len(rows),'worlds;',round(time.perf_counter()-start,1),'sec',flush=True)

def train_cell(payload):
    c,seeds=payload;e=Environment(**c['environment']);m=Mechanism(**c['mechanism']);scores=[];rows=[]
    for j,policy in enumerate(policies()):
        profits=[]
        for seed in seeds:
            w=World(e,m,make_tape(seed,e.opportunities,e.half_life),policy);obs,_=w.run();last=obs[-1]
            assert last['actor_residual']==0
            profits.append(last['actor_profit'])
            rows.append(dict(cell=c['id'],policy=j,seed=seed,profit=last['actor_profit'],peak=last['actor_peak']))
        scores.append(float(np.mean(profits)))
    best=max(range(len(scores)),key=lambda j:(scores[j],-j))
    return dict(cell=c['id'],policy=asdict(policies()[best]),training_mean=scores[best]),rows

def train():
    p=plan();lookup={c['id']:c for c in p['cells']};chosen=[];rows=[];start=time.perf_counter()
    payloads=[(lookup[p['aliases'][alias]],p['training_seeds']) for alias in p['training']]
    with ProcessPoolExecutor(max_workers=3) as pool:
      for selection,results in pool.map(train_cell,payloads):
        chosen.append(selection);rows.extend(results)
        save(OUT/'training.csv.gz',rows)
        print('TRAINED',selection,flush=True)
    write(OUT/'frozen.json',dict(status='frozen_before_confirmation',source_hashes=hashes(),created=now(),selected=chosen,plan_hash=digest(p)))
    write(OUT/'training_manifest.json',dict(status='complete',worlds=len(rows),elapsed=time.perf_counter()-start))

def time_to(rows,field,threshold,start):
    previous=False
    for row in rows:
        valid=(row['time']>=start and row[field] is not None and row[field]>=threshold and row['window_orders']>=5 and row['window_gross']>=100)
        if valid and previous:return row['time']/60
        previous=valid
    return None

def seed_worlds(payload):
    seed,targets,cells=payload;lookup={c['id']:c for c in cells};tapes={}
    observations=[];flows=[];times=[];world_hashes={};traces=[]
    for target in targets:
        c=lookup[target['base']];e=Environment(**c['environment']);m=Mechanism(**c['mechanism'])
        key=(e.opportunities,e.half_life)
        if key not in tapes:tapes[key]=make_tape(seed,*key)
        capture=seed==50000 and target['base'] in ('copies9__original_first','copies9__elected_120s','copies99__original_first')
        w=World(e,m,tapes[key],Policy(**target['policy']),capture);obs,minutes=w.run()
        for row in obs:row.update(cell=target['id'],base=target['base'],kind=target['kind'])
        for row in minutes:row.update(cell=target['id'],kind=target['kind'])
        observations.extend(obs);flows.extend(minutes)
        world_hashes[f'{target["id"]}:{seed}']=digest(obs)
        start_time=max(300,e.first_copy+300)
        times.append(dict(cell=target['id'],base=target['base'],kind=target['kind'],seed=seed,
            top50=time_to(minutes,'top_share',.5,start_time),top70=time_to(minutes,'top_share',.7,start_time),
            original50=time_to(minutes,'original_share',.5,start_time),original70=time_to(minutes,'original_share',.7,start_time),
            lead50=time_to(minutes,'lead_share',.5,start_time),lead70=time_to(minutes,'lead_share',.7,start_time)))
        if capture:traces.append((target['id'],dict(events=w.b.trace,observations=obs)))
    return seed,observations,flows,times,world_hashes,traces

def confirm():
    p=plan();f=json.loads((OUT/'frozen.json').read_text());assert f['source_hashes']==hashes()
    lookup={c['id']:c for c in p['cells']}
    targets=[dict(id=c['id'],base=c['id'],kind='idle',policy=asdict(Policy())) for c in p['cells']]
    for selected in f['selected']:
        family=selected.get('family','overall');prefix='copy_attack__' if family=='copy_only' else 'attack__'
        if family=='copy_only' and selected['policy']['budget']==0:continue
        matched_id='same_policy_A__'+prefix+selected['cell']
        targets.append(dict(id=prefix+selected['cell'],base=selected['cell'],kind='trained',family=family,policy=selected['policy'],matched_id=matched_id))
        c=lookup[selected['cell']]
        if c['mechanism']['rule']!='independent':
            targets.append(dict(id=matched_id,base=c['control'],kind='matched_A',policy=selected['policy'],matched_C=selected['cell']))
    if (OUT/'confirmation.csv.gz').exists():raise RuntimeError('Confirmation already exists')
    write(OUT/'targets.json',targets)
    worlds=0;start=time.perf_counter();hashes_by_world={};done=[]
    with gzip.open(OUT/'confirmation.csv.gz','wt',encoding='utf-8',newline='') as sf,gzip.open(OUT/'minute_flows.csv.gz','wt',encoding='utf-8',newline='') as mf:
        sw=mw=None
        with ProcessPoolExecutor(max_workers=3) as pool:
          for seed,obs,minutes,timing,world_hash,traces in pool.map(seed_worlds,[(seed,targets,p['cells']) for seed in p['confirmation_seeds']]):
            if sw is None:sw=csv.DictWriter(sf,fieldnames=list(obs[0]));sw.writeheader()
            if mw is None:mw=csv.DictWriter(mf,fieldnames=list(minutes[0]));mw.writeheader()
            sw.writerows(obs);mw.writerows(minutes);done.extend(timing);hashes_by_world.update(world_hash);worlds+=len(targets)
            if traces:
                dest=OUT/'traces';dest.mkdir(exist_ok=True)
                for cell,trace in traces:
                    with gzip.open(dest/f'{cell}_{seed}.json.gz','wt',encoding='utf-8') as tf:json.dump(trace,tf,separators=(',',':'))
            if (seed-49999)%10==0:
                sf.flush();mf.flush();write(OUT/'confirmation_manifest.json',dict(status='running',worlds=worlds,expected=len(targets)*100,seed_count=seed-49999,elapsed=time.perf_counter()-start))
                print('CONFIRM',seed-49999,'/100;',worlds,'worlds;',round(time.perf_counter()-start,1),'sec',flush=True)
        for seed in []:
            tapes={}
            for target in targets:
                c=lookup[target['base']];e=Environment(**c['environment']);m=Mechanism(**c['mechanism'])
                key=(e.opportunities,e.half_life)
                if key not in tapes:tapes[key]=make_tape(seed,*key)
                trace=seed==50000 and target['base'] in [p['aliases'][a] for a in ('copies9__original_first','copies9__elected_120s','copies99__original_first')]
                try:
                    w=World(e,m,tapes[key],Policy(**target['policy']),trace);obs,minutes=w.run()
                except Exception:
                    import traceback
                    write(OUT/'failure.json',dict(target=target,seed=seed,traceback=traceback.format_exc()));raise
                for row in obs:row.update(cell=target['id'],base=target['base'],kind=target['kind'])
                for row in minutes:row.update(cell=target['id'],kind=target['kind'])
                if sw is None:sw=csv.DictWriter(sf,fieldnames=list(obs[0]));sw.writeheader()
                if mw is None:mw=csv.DictWriter(mf,fieldnames=list(minutes[0]));mw.writeheader()
                sw.writerows(obs);mw.writerows(minutes)
                hashes_by_world[f'{target["id"]}:{seed}']=digest(obs)
                start_time=max(300,e.first_copy+300)
                done.append(dict(cell=target['id'],base=target['base'],kind=target['kind'],seed=seed,
                    top50=time_to(minutes,'top_share',.5,start_time),top70=time_to(minutes,'top_share',.7,start_time),
                    original50=time_to(minutes,'original_share',.5,start_time),original70=time_to(minutes,'original_share',.7,start_time),
                    lead50=time_to(minutes,'lead_share',.5,start_time),lead70=time_to(minutes,'lead_share',.7,start_time)))
                if trace:
                    dest=OUT/'traces';dest.mkdir(exist_ok=True)
                    with gzip.open(dest/f'{target["id"]}_{seed}.json.gz','wt',encoding='utf-8') as tf:json.dump(dict(events=w.b.trace,observations=obs),tf,separators=(',',':'))
                worlds+=1
            if (seed-49999)%10==0:
                sf.flush();mf.flush()
                write(OUT/'confirmation_manifest.json',dict(status='running',worlds=worlds,expected=len(targets)*100,seed_count=seed-49999,elapsed=time.perf_counter()-start))
                print('CONFIRM',seed-49999,'/100;',worlds,'worlds;',round(time.perf_counter()-start,1),'sec',flush=True)
    save(OUT/'time_to_concentration.csv',done)
    write(OUT/'confirmation_manifest.json',dict(status='complete',worlds=worlds,expected=len(targets)*100,seed_count=100,
        checkpoints=worlds*5,minute_rows=worlds*60,elapsed=time.perf_counter()-start,source_hashes=hashes(),world_hashes=hashes_by_world,failures=0))

def analyze():
    p=plan();manifest=json.loads((OUT/'confirmation_manifest.json').read_text());assert manifest['status']=='complete'
    d=pd.read_csv(OUT/'confirmation.csv.gz');effects=[];summary=[];attacks=[]
    lookup={c['id']:c for c in p['cells']}
    for (cell,label),g in d.groupby(['cell','label']):
        for metric in ('original_share','top_share','lead_share','original_depth','lead_depth','largest_depth','effective_markets','executed','routed','redirected_copy','redirected_original','actor_profit','actor_led','original_creator_cash','copy_creator_cash'):
            mean,lo,hi=ci(g[metric].dropna(),f'summary:{cell}:{label}:{metric}')
            if mean is not None:summary.append(dict(cell=cell,label=label,metric=metric,mean=mean,low=lo,high=hi))
    for c in p['cells']:
        if c['mechanism']['rule']=='independent':continue
        for label in ('5m','15m','30m','60m'):
            a=d[(d.cell==c['control'])&(d.label==label)].set_index('seed').sort_index()
            x=d[(d.cell==c['id'])&(d.label==label)].set_index('seed').sort_index()
            for metric in ('original_share','top_share','original_depth','executed','narrative_executed','top_to_latent','narrative_to_latent','copy_creator_cash'):
                mean,lo,hi=ci(x[metric]-a[metric],f'paired:{c["id"]}:{label}:{metric}')
                effects.append(dict(cell=c['id'],control=c['control'],label=label,metric=metric,A_mean=float(a[metric].mean()),C_mean=float(x[metric].mean()),delta=mean,low=lo,high=hi))
            selected_A=[]
            for seed,row in x.iterrows():
                selected_A.append(json.loads(a.loc[seed,'depth_vector'])[int(row.lead)] if pd.notna(row.lead) else 0.)
            focal=x.lead_depth.fillna(0).to_numpy();mean,lo,hi=ci(focal-np.asarray(selected_A),f'focal:{c["id"]}:{label}')
            effects.append(dict(cell=c['id'],control=c['control'],label=label,metric='same_mint_lead_depth',A_mean=float(np.mean(selected_A)),C_mean=float(np.mean(focal)),delta=mean,low=lo,high=hi))
    targets=json.loads((OUT/'targets.json').read_text())
    for target in targets:
        if target['kind']!='trained':continue
        x=d[(d.cell==target['id'])&(d.label=='exit')].set_index('seed').sort_index()
        idle=d[(d.cell==target['base'])&(d.label=='exit')].set_index('seed').sort_index()
        match_id=target['matched_id']
        matched=d[(d.cell==match_id)&(d.label=='exit')].set_index('seed').sort_index()
        extra=x.actor_profit-matched.actor_profit if len(matched) else x.actor_profit-idle.actor_profit
        mean,lo,hi=ci(extra,f'attack:{target["id"]}')
        at15=d[(d.cell==target['id'])&(d.label=='15m')]
        attacks.append(dict(cell=target['base'],attack_id=target['id'],family=target.get('family','overall'),actor_profit=float(x.actor_profit.mean()),matched_A_profit=float(matched.actor_profit.mean()) if len(matched) else 0,
            extra_profit=mean,low=lo,high=hi,profit_frequency=float((x.actor_profit>0).mean()),actor_led_share=float(at15.actor_led.mean()),
            residual=float(x.actor_residual.max()),peak=float(x.actor_peak.mean()),policy=target['policy']))
    save(OUT/'summaries.csv',summary);save(OUT/'paired_effects.csv',effects);write(OUT/'attack_results.json',attacks)
    print(pd.DataFrame(summary).query("label=='15m' and metric in ['original_share','top_share','original_depth','lead_depth'] and cell.str.startswith('copies')",engine='python').to_string(index=False),flush=True)
    print(json.dumps(attacks,indent=2),flush=True)

if __name__=='__main__':
    {'init':init,'pilot':pilot,'train':train,'confirm':confirm,'analyze':analyze}[sys.argv[1]]()
