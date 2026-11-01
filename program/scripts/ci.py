"""Inspect this branch's GitHub Actions evidence; credentials stay in memory.

Uses the repository's existing Git credential helper. Never writes its response.
Run from the repo root: python program/scripts/ci.py [status|logs|download] [run_id]
"""
import io,json,subprocess,sys,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
API='https://api.github.com/repos/Arriived/bonding-curve'
def get(url,raw=False):
    cred=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True,cwd=ROOT)
    fields=dict(line.split('=',1) for line in cred.stdout.splitlines() if '=' in line)
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+fields['password'],'User-Agent':'program-v1-ci','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=60) as r:data=r.read()
    return data if raw else json.loads(data)
def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'status'
    runs=get(API+'/actions/runs?branch=claude%2Fprogram-v1&per_page=3')['workflow_runs']
    run_id=int(sys.argv[2]) if len(sys.argv)>2 else runs[0]['id']
    if cmd=='status':
        for r in runs:print(json.dumps({k:r[k] for k in ['id','head_sha','status','conclusion','html_url']}))
        for job in get(API+f'/actions/runs/{run_id}/jobs')['jobs']:
            print(json.dumps({'job':job['name'],'status':job['status'],'conclusion':job['conclusion'],'steps':[{k:s.get(k) for k in ['name','status','conclusion']} for s in job['steps']]}))
    elif cmd=='logs':
        data=get(API+f'/actions/runs/{run_id}/logs',True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if '/' not in name:
                    s=z.read(name).decode('utf-8',errors='replace')
                    lines=s.splitlines()
                    hits=[i for i,l in enumerate(lines) if 'error' in l.lower() or 'panicked' in l.lower() or 'test result:' in l or 'CU_REPORT' in l]
                    indices=set()
                    for i in hits:
                        indices.update(range(max(0,i-3),min(len(lines),i+14)))
                    print(name+'\n'+'\n'.join(lines[i] for i in sorted(indices))[-45000:])
    elif cmd=='download':
        out=ROOT/'.tmp/ci_artifacts'/str(run_id);out.mkdir(parents=True,exist_ok=True)
        for a in get(API+f'/actions/runs/{run_id}/artifacts')['artifacts']:
            data=get(a['archive_download_url'],True)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for member in z.infolist():
                    dest=(out/member.filename).resolve()
                    if not dest.is_relative_to(out.resolve()):raise ValueError('unsafe archive path')
                z.extractall(out)
            print(out)
    else:raise ValueError(cmd)
if __name__=='__main__':main()
