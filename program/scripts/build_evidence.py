"""Record exact tool versions, dependency graph, ELF and source hashes after build.

Run from program/. No wallet, deployment keypair or RPC credential is read.
"""
import hashlib,json,re,subprocess,urllib.request,os,tomllib
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
def command(*args):return subprocess.run(args,cwd=HERE,check=True,capture_output=True,text=True).stdout.strip()
def main():
    url='https://raw.githubusercontent.com/anza-xyz/agave/v4.4.0/cost-model/src/block_cost_limits.rs'
    raw=urllib.request.urlopen(url,timeout=45).read();text=raw.decode()
    cap=int(re.search(r'MAX_WRITABLE_ACCOUNT_UNITS: u64 = ([\d_]+)',text)[1].replace('_',''))
    packages=tomllib.loads((HERE/'Cargo.lock').read_text())['package']
    runtime=next(p['version'] for p in packages if p['name']=='solana-program-runtime')
    assert runtime=='4.3.2','Update the disclosed test-runtime version before changing the VM'
    registry=Path(os.environ.get('CARGO_HOME',str(Path.home()/'.cargo')))/'registry/src'
    bundled={}
    for name in ['pinocchio_token_program.so','spl_token_2022-11.0.0.so','spl_associated_token_account-1.1.1.so']:
        candidates=list(registry.glob('*/litesvm-0.18.1/src/programs/elf/'+name));assert candidates,name
        hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in candidates};assert len(hashes)==1
        bundled[name]=next(iter(hashes))
    files=[*sorted((HERE/'programs').rglob('*.rs')),*sorted((HERE/'programs').rglob('Cargo.toml')),
           *sorted((HERE/'test-fixtures').rglob('src/*.rs')),*sorted((HERE/'test-fixtures').glob('*/Cargo.toml')),
           *sorted((HERE/'test-fixtures').glob('*/Cargo.lock')),HERE/'Cargo.lock',HERE/'Cargo.toml',HERE/'Anchor.toml']
    result={'git_commit':command('git','rev-parse','HEAD'),'versions':{name:command(*args) for name,args in {
        'rustc':['rustc','--version'],'cargo':['cargo','--version'],'anchor':['anchor','--version'],
        'cargo_build_sbf':[str(Path.home()/'.cargo/bin/cargo-build-sbf'),'--version'],'solana':['solana','--version'],
        'effective_sbf_rust':[str(Path.home()/'.cache/solana/v1.58/platform-tools/rust/bin/rustc'),'--version']}.items()},
        'writable_account_limit':{'units':cap,'source':url,'sha256':hashlib.sha256(raw).hexdigest()},
        'source_sha256':{p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'elf_sha256':hashlib.sha256((HERE/'target/deploy/doors_v1.so').read_bytes()).hexdigest(),
        'idl_sha256':hashlib.sha256((HERE/'target/idl/doors_v1.json').read_bytes()).hexdigest(),
        'vm':{'litesvm':'0.18.1','agave_runtime':runtime,'feature_profile':'unmodified LiteSVM::new defaults',
              'bundled_program_sha256':bundled,'source':'https://github.com/LiteSVM/litesvm/blob/v0.18.1/crates/litesvm/src/programs/mod.rs'},
        'dependency_tree':command('cargo','tree','--locked'),
        'measurement':'LiteSVM SBF execution; not a devnet/mainnet throughput benchmark'}
    if cluster := os.environ.get('DOORS_SVM_CLUSTER_PROGRAMS'):
        result['vm']['loaded_cluster_programs'] = json.loads((Path(cluster)/'manifest.json').read_text())
    (HERE/'verification/build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Recorded exact toolchain, source/ELF hashes and current Agave writable-account cap.')
if __name__=='__main__':main()
