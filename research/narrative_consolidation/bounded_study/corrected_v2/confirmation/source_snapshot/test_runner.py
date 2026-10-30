"""Fresh evidence locations; workspace temp; unchanged legacy regression suite."""
import argparse,json,sys,tempfile
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--scope',default='all',choices=['mechanics','all','new'])
    a=p.parse_args();out=Path(a.out).resolve()
    if out.exists():raise ValueError('Test output must be a fresh directory')
    out.mkdir(parents=True);tmp=Path.cwd()/'.tmp'/out.name;tmp.mkdir(exist_ok=True)
    tempfile.tempdir=str(tmp)
    import pytest
    args=['-q','-p','no:cacheprovider','--junitxml='+str(out/'tests.xml')]
    if a.scope=='mechanics':args+=['tests/narrative/test_ledger.py']
    elif a.scope=='new':args+=['tests/narrative']
    started=datetime.now(timezone.utc).isoformat()
    with (out/'tests.log').open('w',encoding='utf-8') as f,redirect_stdout(f),redirect_stderr(f):code=pytest.main(args)
    (out/'manifest.json').write_text(json.dumps({'started':started,'finished':datetime.now(timezone.utc).isoformat(),'exit_code':int(code),'scope':a.scope},indent=2))
    print((out/'tests.log').read_text(encoding='utf-8')[-6000:]);return int(code)


if __name__=='__main__':raise SystemExit(main())
