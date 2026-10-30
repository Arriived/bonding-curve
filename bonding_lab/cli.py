"""Command-line reproducible research workflow."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from .experiments import provenance, research_suite
from .simulation import Config, SCENARIOS, run


def main(argv=None):
    parser = argparse.ArgumentParser(description="Shared Bonding Lab — synthetic off-chain research")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "research"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--events", type=int, default=10000 if name=="research" else 2000)
        p.add_argument("--seed", type=int, default=42)
        p.add_argument("--tokens", type=int, default=10)
        p.add_argument("--traders", type=int, default=100)
        p.add_argument("--coupling", type=float, default=.25)
        p.add_argument("--fee", type=float, default=.003)
        p.add_argument("--p0", type=float, default=.01)
        p.add_argument("--k", type=float, default=.0001)
        p.add_argument("--initial-supply", type=float, default=1000)
        p.add_argument("--trade-size", type=float, default=20)
        p.add_argument("--buy-pressure", type=float, default=.55)
        p.add_argument("--volatility", type=float, default=.8)
        if name == "research":
            p.add_argument("--seeds", type=int, default=100)
            p.add_argument("--scenarios", choices=SCENARIOS, nargs="+", default=list(SCENARIOS))
            p.add_argument("--bases", choices=("equal_supplies","equal_capital"), nargs="+", default=["equal_supplies","equal_capital"])
        else:
            p.add_argument("--scenario", choices=SCENARIOS, default="baseline")
    args = parser.parse_args(argv)
    config = Config(**{k:getattr(args,k) for k in ("events","seed","tokens","traders","coupling","fee","p0","k","initial_supply","trade_size","buy_pressure","volatility")})
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Output directory must be new or empty to protect earlier results")
    if args.command == "research":
        manifest = research_suite(args.out, config, args.seeds, args.scenarios, args.bases)
        print(json.dumps(manifest, indent=2))
    else:
        config = replace(config, scenario=args.scenario)
        result = run(config)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out/"run.zip").write_bytes(result.export_zip())
        (args.out/"manifest.json").write_text(json.dumps(provenance(config,status="complete"), indent=2),encoding="utf-8")
        print(json.dumps(result.metrics, indent=2))


if __name__ == "__main__":
    main()
