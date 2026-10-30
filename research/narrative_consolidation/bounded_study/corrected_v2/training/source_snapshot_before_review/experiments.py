"""Sequential pilot -> attack training -> immutable freeze -> confirmation."""
from dataclasses import asdict,replace
from datetime import datetime,timezone
from pathlib import Path
import csv,gzip,hashlib,json,shutil,time,traceback
import numpy as np
from .model import Config,Policy,make_tape,run,hash_obj,canonical,World
from .attacks import policies,ordering_study


def now():return datetime.now(timezone.utc).isoformat()
def write_json(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def fresh(path):
    if path.exists():raise ValueError(f'Output already exists: {path}')
    path.mkdir(parents=True);return path


def sources():
    return {p.as_posix():hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
            for p in sorted(Path('bonding_lab/narrative').glob('*.py'))}


def matrix():
    cells=[];seen=set()
    def add(c):
        key=asdict(c);key.pop('name')
        digest=hash_obj(key)
        if digest not in seen:cells.append(c);seen.add(digest)
    a=Config();b=Config(name='B',arch='B');c=Config(name='C',arch='C')
    d=Config(name='D',arch='D',rule='commit')
    for x in (a,b,c,d):add(x)
    for mode,name in [('creator_lock','B_CREATOR'),('protocol_destroy','B_DESTROY'),('creator_destroy','B_CREATOR_DESTROY')]:add(replace(b,name=name,support_mode=mode))
    add(Config(name='SINGLE_SPOT',arch='single_spot'))
    add(Config(name='SINGLE_BATCH',arch='single_batch',rule='commit'))
    add(Config(name='INDEPENDENT_BATCH',arch='independent_batch',rule='commit'))
    add(Config(name='SPOT_LOCK',arch='locked_spot'))
    for i in range(11):add(replace(c,name=f'C_ACCEPT_{i}',acceptance=i/10))
    for x in (0,.25,1):add(replace(c,name=f'C_REACH_{x}',reach=x))
    for pref,out,name in [(0,0,'LEAVE'),(1,0,'PREFERRED'),(0,1,'OUTSIDE')]:add(replace(c,name=f'C_REJECT_{name}',reject_preferred=pref,reject_outside=out))
    for x in (0,.5,1):add(replace(c,name=f'C_MIGRATE_{x}',migration=x))
    for x in (0,.25,1):add(replace(d,name=f'D_BROAD_{x}',broad=x))
    for x in (0,.25,1):add(replace(d,name=f'D_LOCK_{x}',lock_willingness=x))
    add(replace(d,name='D_TIME',rule='timecommit'))
    for base in (a,c):
        for rule in ('commit','timecommit'):add(replace(base,name=f'{base.name}_{rule.upper()}',rule=rule,overlay=True))
        for rule in ('holders','concentration'):add(replace(base,name=f'{base.name}_{"HOLDERS" if rule=="holders" else "HHI"}',rule=rule))
    for base in (b,c,d):
        for feedback in (-.3,.3):add(replace(base,name=f'{base.name}_ATTENTION_{feedback}',feedback=feedback))
    for base in (a,b,c,d):add(replace(base,name=f'{base.name}_COLLAPSE',collapse=True))
    for base in (c,d):add(replace(base,name=f'{base.name}_MISGROUP',grouping=True))
    for base in (a,b,c,d):add(replace(base,name=f'{base.name}_REFUSAL',refusal=.5))
    for base in (a,b,c,d):add(replace(base,name=f'{base.name}_NO_WINNER',no_winner=True))
    for base in (b,c,d):
        add(replace(base,name=f'{base.name}_TIE',force_tie=True))
        add(replace(base,name=f'{base.name}_WITHHELD',withheld=True))
        add(replace(base,name=f'{base.name}_DELAY',delay=3600))
        add(replace(base,name=f'{base.name}_RANDOM_CLOSE',random_close=True))
    add(replace(d,name='D_TIMEOUT',delay=8000))
    return cells


def pilot(root):
    out=fresh(root/'pilot');started=time.perf_counter();rows=[];times=[]
    chosen=[c for c in matrix() if c.name in ('A','B','C','D','C_ACCEPT_0','C_ACCEPT_10','SINGLE_SPOT','SINGLE_BATCH','INDEPENDENT_BATCH')]
    for seed in range(20):
        tape=make_tape(seed)
        for c in chosen:
            tick=time.perf_counter();observations,_,_=run(c,tape)
            times.append(time.perf_counter()-tick)
            rows.append(next(r for r in observations if r['label']=='plus_7d'))
    save_csv(out/'runs.csv',rows)
    write_json(out/'manifest.json',dict(status='complete',created=now(),seeds=list(range(20)),
               configurations=[asdict(c) for c in chosen],worlds=len(rows),elapsed=time.perf_counter()-started,
               mean_world_seconds=float(np.mean(times)),max_world_seconds=max(times),
               reserve_sample_sd={c.name:float(np.std([r['cohort_reserve'] for r in rows if r['name']==c.name],ddof=1)) for c in chosen},sources=sources()))
    save_csv(out/'ordering_search.csv',ordering_study())
    print(json.dumps(json.loads((out/'manifest.json').read_text()) ,indent=2)[:1800],flush=True)


def save_csv(path,rows):
    if not rows:return
    keys=list(rows[0]);opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'wt',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)


def train(root):
    out=fresh(root/'training');started=time.perf_counter();rows=[];selected=[]
    chosen=[c for c in matrix() if c.name in ('A','B','B_CREATOR','C','D','A_HOLDERS','C_HOLDERS','C_HHI','D_TIME')]
    tapes={seed:make_tape(seed) for seed in range(100,150)}
    for c in chosen:
        candidates=policies(c.arch=='D')
        scores={};by_policy={}
        for pi,p in enumerate(candidates):
            results=[]
            for seed,tape in tapes.items():
                obs,_,_=run(c,tape,p);terminal=obs[-1];results.append(terminal)
                rows.append(dict(config=c.name,policy_id=pi,policy=canonical(asdict(p)),seed=seed,
                                 profit=terminal['attacker_cash_pnl'],peak=terminal['attacker_peak'],
                                 fees=terminal['attacker_fees'],acquisition=terminal['attacker_acquisition'],
                                 residual=terminal['attacker_residual'],capture=terminal['captured']))
            scores[pi]=float(np.mean([r['attacker_cash_pnl'] for r in results])) if all(r['attacker_residual']==0 for r in results) else -1e30
            by_policy[pi]=results
        families=sorted({p.family for p in candidates if p.family!='idle'})
        for family in families:
            eligible=[i for i,p in enumerate(candidates) if p.family in ('idle',family)]
            best=max(eligible,key=lambda i:(scores[i],-i))
            selected.append(dict(config=c.name,family=family,policy=asdict(candidates[best]),
                                 training_mean_profit=scores[best],candidate_count=len(eligible)))
        print('Training complete:',c.name,len(candidates)*50,'worlds',flush=True)
        save_csv(out/'search_rows.csv.gz',rows)
    write_json(out/'selected.json',selected)
    write_json(out/'manifest.json',dict(status='complete',created=now(),seeds=list(range(100,150)),
               worlds=len(rows),elapsed=time.perf_counter()-started,objective='Mean feasible complete-exit cash P&L; abstention eligible in every family',
               configurations=[asdict(c) for c in chosen],sources=sources()))


def freeze(root):
    if (root/'frozen_plan.json').exists():raise ValueError('Frozen plan already exists')
    for name in ('pilot','training'):
        if json.loads((root/name/'manifest.json').read_text())['status']!='complete':raise ValueError('Prior stage incomplete')
    configs=matrix();lookup={c.name:c for c in configs}
    targets=[dict(name=c.name,base=c.name,config=asdict(c),policy=asdict(Policy()),kind='no_attack') for c in configs]
    selections=json.loads((root/'training/selected.json').read_text())
    for selection in selections:
        if selection['policy']['family']=='idle':continue
        base=lookup[selection['config']];name=f"ATTACK_{base.name}_{selection['family']}"
        targets.append(dict(name=name,base=base.name,config=asdict(replace(base,name=name)),
                            policy=selection['policy'],kind='trained_attack'))
    obj=dict(created=now(),status='frozen_before_confirmation',seeds=list(range(10000,10100)),
             opportunities_per_tape=480,targets=targets,source_sha256=sources(),
             attack_selections=selections,pilot_manifest_sha256=hashlib.sha256((root/'pilot/manifest.json').read_bytes()).hexdigest(),
             model_uncertainty='Synthetic assumptions; sampling intervals are conditional on this model',
             excluded='No dashboard, deployment, real funds, calibration, full factorial, external dealer, leverage, or proof of attack optimality')
    write_json(root/'frozen_plan.json',obj)
    print('Frozen',len(configs),'no-attack cells,',len(targets)-len(configs),'trained attack cells;',len(targets)*100,'planned worlds',flush=True)


def confirm(root):
    plan=json.loads((root/'frozen_plan.json').read_text())
    if sources()!=plan['source_sha256']:raise ValueError('Code differs from pre-confirmation frozen source')
    out=fresh(root/'confirmation');fresh(out/'tapes');fresh(out/'traces');fresh(out/'source_snapshot')
    for path in plan['source_sha256']:
        shutil.copy2(path,out/'source_snapshot'/Path(path).name)
    counts=default_counts(plan);started=time.perf_counter();tape_hashes={};done=0
    manifest=dict(status='running',started=now(),planned_worlds=len(plan['targets'])*100,
                  frozen_plan_sha256=hashlib.sha256((root/'frozen_plan.json').read_bytes()).hexdigest(),
                  completed_worlds=0,completed_by_cell=counts,failures=0,source_sha256=sources())
    write_json(out/'manifest.json',manifest)
    writer=None
    try:
        with gzip.open(out/'runs.csv.gz','wt',newline='',encoding='utf-8') as f, (out/'failures.jsonl').open('w',encoding='utf-8') as failures:
            for seed in plan['seeds']:
                tape=make_tape(seed);tape_hashes[str(seed)]=tape['_sha256']
                with gzip.open(out/'tapes'/f'{seed}.json.gz','wt',encoding='utf-8') as tf:tf.write(canonical(tape))
                for target in plan['targets']:
                    c=Config(**target['config']);p=Policy(**target['policy'])
                    try:
                        world=World(c,tape,p,capture=seed==10000)
                        rows,trace,rank=world.run()
                    except Exception:
                        failures.write(json.dumps(dict(seed=seed,target=target,traceback=traceback.format_exc()))+'\n');failures.flush()
                        manifest['failures']+=1;raise
                    for row in rows:
                        row.update(base=target['base'],kind=target['kind'],config_hash=hash_obj(target['config']),policy_hash=hash_obj(target['policy']))
                    if writer is None:writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
                    writer.writerows(rows);done+=1;counts[target['name']]+=1
                    if trace is not None:
                        with gzip.open(out/'traces'/f"{target['name']}_{seed}.json.gz",'wt',encoding='utf-8') as tf:
                            tf.write(canonical(dict(events=trace,rankings=rank,
                                terminal_wallets={o:dict(cash=world.b.cash[o],claims={str(i):world.b.hold.get((o,i),0) for i in range(11)}) for o in list(world.initial_trader)+world.actor})))
                f.flush();manifest.update(completed_worlds=done,completed_by_cell=counts,elapsed=time.perf_counter()-started)
                write_json(out/'manifest.json',manifest)
                if (seed-9999)%5==0:print(f'Confirmation {seed-9999}/100 seeds; {done} worlds; {manifest["elapsed"]:.1f}s',flush=True)
        manifest.update(status='complete',finished=now(),elapsed=time.perf_counter()-started,
                        tape_hashes=tape_hashes,raw_results_sha256=hashlib.sha256((out/'runs.csv.gz').read_bytes()).hexdigest())
    except BaseException:
        manifest.update(status='failed_or_interrupted',finished=now(),completed_worlds=done)
        write_json(out/'manifest.json',manifest);raise
    write_json(out/'manifest.json',manifest)


def default_counts(plan):return {x['name']:0 for x in plan['targets']}


def verify_preservation(root):
    old=json.loads((root/'preservation_before.json').read_text());changed=[]
    for name,row in old['files'].items():
        p=Path(name)
        if not p.exists() or hashlib.file_digest(p.open('rb'),'sha256').hexdigest()!=row['sha256']:changed.append(name)
    result=dict(checked=now(),original_files=len(old['files']),changed=changed,status='passed' if not changed else 'failed')
    write_json(root/'preservation_after.json',result)
    print(json.dumps(result,indent=2))
    if changed:raise AssertionError('Preexisting files changed')
