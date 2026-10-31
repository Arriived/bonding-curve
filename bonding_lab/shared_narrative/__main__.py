"""python -m bonding_lab.shared_narrative {main,linear,shock,sensitivity,wash,spam,bundle,report,all}"""
import argparse

from .experiments import run_stage

STAGES = ("main", "linear", "shock", "sensitivity", "wash", "spam", "bundle")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=STAGES+("report", "all"))
    ap.add_argument("--out", default="research/shared_narrative/outputs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--quick", action="store_true", help="few seeds; smoke test only")
    a = ap.parse_args()
    stages = STAGES if a.stage == "all" else (() if a.stage == "report" else (a.stage,))
    for s in stages:
        m = run_stage(s, a.out, a.workers, a.quick)
        print(s, "done in", m["elapsed_s"], "s", flush=True)
    if a.stage in ("report", "all"):
        from .report import build
        build(a.out)


if __name__ == "__main__":
    main()
