"""Record exact tool versions, dependency graph, ELF and source hashes after build.

Run from program/. No wallet, deployment keypair or RPC credential is read.
"""
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
def command(*args):return subprocess.run(args,cwd=HERE,check=True,capture_output=True,text=True).stdout.strip()
def main():
    url='https://raw.githubusercontent.com/anza-xyz/agave/v4.4.0/cost-model/src/block_cost_limits.rs'
    raw=urllib.request.urlopen(url,timeout=45).read();text=raw.decode()
    cap=int(re.search(r'MAX_WRITABLE_ACCOUNT_UNITS: u64 = ([\d_]+)',text)[1].replace('_',''))
    files=[*sorted((HERE/'programs').rglob('*.rs')),HERE/'Cargo.lock',HERE/'Cargo.toml',HERE/'Anchor.toml']
    result={'git_commit':command('git','rev-parse','HEAD'),'versions':{name:command(*args) for name,args in {
        'rustc':['rustc','--version'],'cargo':['cargo','--version'],'anchor':['anchor','--version'],
        'cargo_build_sbf':['cargo-build-sbf','--version'],'solana':['solana','--version']}.items()},
        'writable_account_limit':{'units':cap,'source':url,'sha256':hashlib.sha256(raw).hexdigest()},
        'source_sha256':{p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'elf_sha256':hashlib.sha256((HERE/'target/deploy/doors_v1.so').read_bytes()).hexdigest(),
        'dependency_tree':command('cargo','tree','--locked'),
        'measurement':'LiteSVM SBF execution; not a devnet/mainnet throughput benchmark'}
    (HERE/'verification/build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Recorded exact toolchain, source/ELF hashes and current Agave writable-account cap.')
if __name__=='__main__':main()
