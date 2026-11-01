"""Resumable, compressed public-RPC observations and collection telemetry."""
import contextlib
import datetime
import email.utils
import gzip
import hashlib
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import urllib.parse

from audit_liveness_brief import OUT

PATH=OUT/'consolidation_history.sqlite'
RPC='https://api.mainnet-beta.solana.com'


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def retry_delay(error,attempt):
    headers=getattr(error,'headers',None)
    try:hint=float(headers.get('Retry-After',0)) if headers else 0
    except (TypeError,ValueError):
        try:hint=max(0,(email.utils.parsedate_to_datetime(headers['Retry-After'])-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
        except (TypeError,ValueError,KeyError):hint=0
    return max(hint,10 if getattr(error,'code',None)==429 else 0,min(2**attempt,30))


class RPCError(Exception):
    def __init__(self,error):
        self.error=error
        super().__init__(str(error))


class Cache:
    def __init__(self,path=PATH,qps=3.0):
        self.path=path;self.interval=1/qps;self.lock=threading.Lock();self.next_call=0;self.blocked_until=0;self.readers=threading.local()
        self.rpc_url=os.environ.get('SOLANA_RPC_URL') or RPC
        self.provider=hashlib.sha256(self.rpc_url.encode()).hexdigest()
        with contextlib.closing(sqlite3.connect(path,timeout=60)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS rpc(key TEXT PRIMARY KEY,method TEXT NOT NULL,params TEXT NOT NULL,
                    started TEXT NOT NULL,finished TEXT NOT NULL,body BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,method TEXT,started TEXT,finished TEXT,
                    seconds REAL,http_status INTEGER,rpc_error TEXT,received_bytes INTEGER);
                CREATE TABLE IF NOT EXISTS study(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY,started TEXT,finished TEXT,requests TEXT,body BLOB);
                CREATE TABLE IF NOT EXISTS rpc_sources(key TEXT PRIMARY KEY,provider TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS http_errors(id INTEGER PRIMARY KEY,method TEXT,started TEXT,status INTEGER,body BLOB);
            ''')
            db.commit()
        self.put_study('provider:'+self.provider,{'host':urllib.parse.urlsplit(self.rpc_url).hostname,
            'default_public_endpoint':self.rpc_url==RPC,'override_variable':'SOLANA_RPC_URL'})

    def get(self,method,params):
        encoded=json.dumps(params,sort_keys=True,separators=(',',':'))
        key=hashlib.sha256((method+'\n'+encoded).encode()).hexdigest()
        if not hasattr(self.readers,'db'):
            self.readers.db=sqlite3.connect(self.path,timeout=60,isolation_level=None)
        row=self.readers.db.execute('SELECT body FROM rpc WHERE key=?',(key,)).fetchone()
        if row:return json.loads(gzip.decompress(row[0]))
        return None

    def pace(self,count=1):
        while True:
            with self.lock:
                now=time.monotonic();wait=max(self.next_call,self.blocked_until)-now
                if wait<=0:
                    self.next_call=now+count*self.interval;return
            time.sleep(wait)

    def cooldown(self,seconds):
        with self.lock:self.blocked_until=max(self.blocked_until,time.monotonic()+seconds)

    def call(self,method,params):
        hit=self.get(method,params)
        if hit is not None:
            if 'error' in hit:raise RPCError(hit['error'])
            return hit['result']
        encoded=json.dumps(params,sort_keys=True,separators=(',',':'))
        key=hashlib.sha256((method+'\n'+encoded).encode()).hexdigest()
        for attempt in range(7):
            self.pace()
            start=utc();tick=time.monotonic();status=None;error=None;raw=None;value=None;network_error=None
            try:
                payload=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
                req=urllib.request.Request(self.rpc_url,data=payload,headers={'Content-Type':'application/json','User-Agent':'bonding-curve-research/1.0'})
                with urllib.request.urlopen(req,timeout=30) as response:
                    status=response.status;raw=response.read()
                value=json.loads(raw)
                if 'error' in value:
                    error=value['error']
            except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:
                status=getattr(exc,'code',None);error={'network':str(exc)};network_error=exc
                if isinstance(exc,urllib.error.HTTPError):raw=exc.read()
            finish=utc()
            with contextlib.closing(sqlite3.connect(self.path,timeout=60)) as db:
                db.execute('INSERT INTO attempts(method,started,finished,seconds,http_status,rpc_error,received_bytes) VALUES(?,?,?,?,?,?,?)',
                    (method,start,finish,time.monotonic()-tick,status,json.dumps(error) if error else None,len(raw) if raw else 0))
                if status not in (None,200) and raw is not None:
                    db.execute('INSERT INTO http_errors(method,started,status,body) VALUES(?,?,?,?)',(method,start,status,gzip.compress(raw,mtime=0)))
                db.commit()
            if status not in {None,200,429,500,502,503,504}:raise RPCError(error)
            retry=error and ('network' in error or error.get('code') in {429,-32429,-32005,-32004,-32019})
            if retry:
                if attempt==6:raise RPCError(error)
                delay=max(retry_delay(network_error,attempt),10 if error.get('code') in {429,-32429} else 0)
                if status==429 or error.get('code') in {429,-32429}:self.cooldown(delay)
                time.sleep(delay);continue
            if value is None:raise RPCError(error)
            with contextlib.closing(sqlite3.connect(self.path,timeout=60)) as db:
                db.execute('INSERT OR IGNORE INTO rpc VALUES(?,?,?,?,?,?)',
                    (key,method,encoded,start,finish,gzip.compress(raw,mtime=0)))
                db.execute('INSERT OR IGNORE INTO rpc_sources VALUES(?,?)',(key,self.provider))
                db.commit()
            if error:raise RPCError(error)
            return value['result']
        raise RuntimeError('unreachable')

    def put_study(self,key,value):
        with contextlib.closing(sqlite3.connect(self.path,timeout=60)) as db:
            db.execute('INSERT OR REPLACE INTO study VALUES(?,?)',(key,json.dumps(value,sort_keys=True)))
            db.commit()

    def study(self,key):
        with contextlib.closing(sqlite3.connect(self.path,timeout=60)) as db:
            row=db.execute('SELECT value FROM study WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None

    def checkpoint(self):
        with contextlib.closing(sqlite3.connect(self.path,timeout=60)) as db:
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def call_many(self, requests):
        """Cache a small JSON-RPC batch, pacing logical calls rather than HTTP posts.

        Successful subresponses survive partial errors. Retries request only the
        remaining items. Raw batch envelopes are retained as well as each reply.
        """
        results = [None] * len(requests)
        pending = []
        for index, (method, params) in enumerate(requests):
            hit = self.get(method, params)
            if hit is not None:
                if 'error' in hit: raise RPCError(hit['error'])
                results[index] = hit['result']
            else: pending.append(index)
        for attempt in range(7):
            if not pending: return results
            self.pace(len(pending))
            payload = [{'jsonrpc':'2.0', 'id':i, 'method':requests[i][0], 'params':requests[i][1]} for i in pending]
            start=utc(); tick=time.monotonic(); status=None; raw=None; error=None;network_error=None
            try:
                req=urllib.request.Request(self.rpc_url, data=json.dumps(payload).encode(),
                    headers={'Content-Type':'application/json','User-Agent':'bonding-curve-research/1.0'})
                with urllib.request.urlopen(req,timeout=60) as response:
                    status=response.status;raw=response.read()
                value=json.loads(raw)
                if not isinstance(value,list): raise RPCError(value)
            except (urllib.error.URLError,TimeoutError,ConnectionError,RPCError) as exc:
                status=getattr(exc,'code',status); error=str(exc);value=[];network_error=exc
                if isinstance(exc,urllib.error.HTTPError):raw=exc.read()
            finish=utc(); replies={r['id']:r for r in value if isinstance(r,dict) and 'id' in r}
            remaining=[];permanent_error=None
            with contextlib.closing(sqlite3.connect(self.path,timeout=60)) as db:
                db.execute('INSERT INTO attempts(method,started,finished,seconds,http_status,rpc_error,received_bytes) VALUES(?,?,?,?,?,?,?)',
                    ('batch:'+str(len(pending))+':'+requests[pending[0]][0],start,finish,time.monotonic()-tick,status,error,len(raw) if raw else 0))
                db.execute('INSERT INTO batches(started,finished,requests,body) VALUES(?,?,?,?)',
                    (start,finish,json.dumps(payload,separators=(',',':')),gzip.compress(raw,mtime=0) if raw else None))
                for index in pending:
                    reply=replies.get(index)
                    if reply is None or ('error' in reply and reply['error'].get('code') in {429,-32429,-32005,-32004,-32019}):
                        remaining.append(index);continue
                    method,params=requests[index]
                    encoded=json.dumps(params,sort_keys=True,separators=(',',':'))
                    key=hashlib.sha256((method+'\n'+encoded).encode()).hexdigest()
                    db.execute('INSERT OR IGNORE INTO rpc VALUES(?,?,?,?,?,?)',
                        (key,method,encoded,start,finish,gzip.compress(json.dumps(reply,separators=(',',':')).encode(),mtime=0)))
                    db.execute('INSERT OR IGNORE INTO rpc_sources VALUES(?,?)',(key,self.provider))
                    if 'error' in reply: permanent_error=reply['error']
                    else: results[index]=reply['result']
                db.commit()
            if permanent_error:raise RPCError(permanent_error)
            if status not in {None,200,429,500,502,503,504}:raise RPCError({'http_status':status,'error':error})
            pending=remaining
            if pending:
                if attempt==6: raise RPCError({'unresolved_batch_items':len(pending),'last_error':error})
                limited=status==429 or any(r.get('error',{}).get('code') in {429,-32429} for r in replies.values())
                delay=max(retry_delay(network_error,attempt),10 if limited else 0)
                if limited:self.cooldown(delay)
                time.sleep(delay)
        raise RuntimeError('unreachable')


def readonly(path=PATH):
    return sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)
