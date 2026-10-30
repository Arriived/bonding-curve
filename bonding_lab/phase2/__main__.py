import argparse
import json
from pathlib import Path
from .world import Study
from .research import run_suite


def main():
    p=argparse.ArgumentParser(description="Phase 2: matched-capital liquidity, external arbitrage and inventory risk")
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--seeds",type=int,default=100)
    p.add_argument("--events",type=int,default=500)
    p.add_argument("--tokens",type=int,default=10)
    p.add_argument("--capital",type=float,default=10000)
    p.add_argument("--fee",type=float,default=.003)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--volatility",type=float,default=.02)
    p.add_argument("--scenarios",nargs="+",choices=("baseline","divergent","crash","toxic_admission","joint_run"),default=["baseline","divergent","crash","toxic_admission","joint_run"])
    a=p.parse_args()
    c=Study(tokens=a.tokens,capital=a.capital,fee=a.fee,events=a.events,seed=a.seed,volatility=a.volatility)
    print(json.dumps(run_suite(a.out,c,a.seeds,a.scenarios),indent=2))


if __name__=="__main__":main()
