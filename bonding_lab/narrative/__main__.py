import argparse
from pathlib import Path
from . import experiments as e


def main():
    p=argparse.ArgumentParser(description='Off-chain bounded narrative comparison')
    p.add_argument('command',choices=['init','pilot','train','freeze','confirm','report','verify','replay'])
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--name');p.add_argument('--seed',type=int);p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.command=='init':return e.initialize(a.root)
    if a.command=='replay':
        if a.name is None or a.seed is None or a.out is None:p.error('replay requires --name --seed --out')
        return e.replay(a.root,a.name,a.seed,a.out)
    a.root.mkdir(parents=True,exist_ok=True)
    if a.command=='report':
        from .report import build_report
        return build_report(a.root)
    functions=dict(pilot=e.pilot,train=e.train,freeze=e.freeze,confirm=e.confirm,verify=e.verify_preservation)
    return functions[a.command](a.root)


if __name__=='__main__':main()
