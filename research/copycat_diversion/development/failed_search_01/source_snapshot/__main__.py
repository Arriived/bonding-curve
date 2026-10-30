import argparse,json
from .experiments import run_study


def main():
    p=argparse.ArgumentParser(description="Synthetic copycat diversion: matched variants and adaptive policy search")
    p.add_argument("--out",required=True)
    p.add_argument("--mode",choices=("smoke","study","full"),default="study")
    p.add_argument("--train-events",type=int,default=160)
    p.add_argument("--screen-events",type=int,default=240)
    p.add_argument("--screen-seeds",type=int,default=6)
    p.add_argument("--confirm-seeds",type=int,default=30)
    p.add_argument("--finalists",type=int,default=12)
    p.add_argument("--confusion",type=float,default=.35)
    p.add_argument("--informed",type=float,default=.2)
    p.add_argument("--attacker-capital",type=float,default=1100000.)
    p.add_argument("--launch-cost",type=float,default=10.)
    p.add_argument("--gas",type=float,default=.05)
    a=p.parse_args()
    overrides={k:getattr(a,k) for k in ("confusion","informed","attacker_capital","launch_cost","gas")}
    print(json.dumps(run_study(a.out,a.mode,a.train_events,a.screen_events,a.screen_seeds,a.confirm_seeds,a.finalists,overrides),indent=2))


if __name__=="__main__":main()
