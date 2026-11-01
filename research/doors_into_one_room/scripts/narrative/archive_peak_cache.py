"""Export/restore a consistent compressed SQLite history in Git-sized parts."""
import argparse
import contextlib
import gzip
import hashlib
import json
import pathlib
import shutil
import sqlite3
import tempfile

from audit_liveness_brief import OUT,ROOT
from history_cache import PATH, utc

ARCHIVE=OUT/'peak_history_archive'
CHUNK=20*1024*1024
WORK=ROOT/'.tmp'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    WORK.mkdir(exist_ok=True)
    if args.restore:
        if PATH.exists():raise SystemExit('Refusing to replace an existing working cache.')
        manifest=json.loads((ARCHIVE/'manifest.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(dir=WORK) as td:
            assert pathlib.Path(td).resolve().is_relative_to(WORK.resolve())
            packed=pathlib.Path(td)/'history.gz'
            with packed.open('wb') as output:
                for part in manifest['parts']:
                    source=ARCHIVE/part['name'];assert sha(source)==part['sha256']
                    with source.open('rb') as f:shutil.copyfileobj(f,output)
            with gzip.open(packed,'rb') as f, PATH.open('wb') as output:shutil.copyfileobj(f,output)
        assert sha(PATH)==manifest['database_sha256']
        with contextlib.closing(sqlite3.connect(PATH)) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        print('Restored verified working history cache.');return
    ARCHIVE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORK) as td:
        assert pathlib.Path(td).resolve().is_relative_to(WORK.resolve())
        snapshot=pathlib.Path(td)/'history.sqlite';packed=pathlib.Path(td)/'history.gz'
        with contextlib.closing(sqlite3.connect(PATH)) as source,contextlib.closing(sqlite3.connect(snapshot)) as target:source.backup(target)
        with snapshot.open('rb') as source,packed.open('wb') as target:
            with gzip.GzipFile(filename='',fileobj=target,mode='wb',mtime=0) as compressed:shutil.copyfileobj(source,compressed)
        parts=[]
        with packed.open('rb') as f:
            for index in range(10000):
                data=f.read(CHUNK)
                if not data:break
                name=f'history.sqlite.gz.part{index:03d}'
                (ARCHIVE/name).write_bytes(data)
                parts.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        with contextlib.closing(sqlite3.connect(snapshot)) as db:
            methods=dict(db.execute('SELECT method,COUNT(*) FROM rpc GROUP BY method').fetchall())
            integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        manifest={'exported_at_utc':utc(),'format':'concatenate ordered parts, gzip-decompress to SQLite',
            'database_sha256':sha(snapshot),'database_bytes':snapshot.stat().st_size,'integrity_check':integrity,
            'rpc_response_counts':methods,'parts':parts,'restore_command':'python scripts/narrative/archive_peak_cache.py --restore',
            'contents':'Raw compressed RPC replies, batch envelopes, query parameters, timestamps, request telemetry and study checkpoints.'}
        (ARCHIVE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
        # Delete only obsolete parts in this explicitly scoped archive folder.
        keep={p['name'] for p in parts}
        for obsolete in ARCHIVE.glob('history.sqlite.gz.part*'):
            if obsolete.name not in keep:obsolete.unlink()
        print(json.dumps({k:v for k,v in manifest.items() if k!='parts'},indent=2))


if __name__=='__main__':main()
