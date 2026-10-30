import argparse
from pathlib import Path
from . import experiments as e


def main():
    p=argparse.ArgumentParser(description='Off-chain bounded narrative comparison')
    p.add_argument('command',choices=['pilot','train','freeze','confirm','report','verify'])
    p.add_argument('--root',required=True,type=Path)
    a=p.parse_args();a.root.mkdir(parents=True,exist_ok=True)
    if a.command=='report':
        from .report import build_report
        return build_report(a.root)
    functions=dict(pilot=e.pilot,train=e.train,freeze=e.freeze,confirm=e.confirm,verify=e.verify_preservation)
    return functions[a.command](a.root)


if __name__=='__main__':main()
