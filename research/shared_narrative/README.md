# Shared narrative curve vs independent launches

Off-chain synthetic research. The question: when a narrative breaks and ten
memes launch around it, would one shared curve with ten skins have produced one
runner instead of ten $50k deaths? It also asks whether that would recruit
creators.

- [DESIGN.md](DESIGN.md): the two arms, attention model, matching scheme and
  exact pre-simulation results. Written before the runs.
- [FINDINGS.md](FINDINGS.md): results and verdict.
- `outputs/tables.md`: every generated table, with CIs.
- `outputs/summary.json`: the same numbers in machine-readable form.

## Code (`bonding_lab/shared_narrative/`)

| module | role |
| --- | --- |
| `curves.py` | `PumpShape` (constant product with virtual reserves, graduation to a locked-LP pool) and `LinearShape` (the existing engine's curve at coupling 0) |
| `book.py` | `SkinBook`: skins (mints) mapped to reserve-holding curves. Arm A = identity map, Arm B = all skins → curve 0. Wallet constraints, fee split, gas, conservation check |
| `reference.py` | Decimal reference for the pump shape (reuses `engine.precise`, `decimal`, `RejectedTrade`). The linear reference is `engine.Curve` itself |
| `tape.py` | Matched tapes: launches, arrivals, budgets, exits, attention-process picks, scheduled agent buys |
| `world.py` | Runs one tape in one arm. Asserts conservation and the zero-sum identity on every run |
| `experiments.py` | Matched-seed stages, plus attack searches on training seeds with frozen best responses confirmed on held-out seeds |
| `stats.py`, `report.py` | Bootstrap and seed-cluster CIs, CARA certainty equivalents, SSD test, tables |

Tests: `tests/shared_narrative/`. They cover linear-mode parity with `FastBook`
and `engine.Curve` at coupling 0 (A) and 1 (B), pump float vs Decimal parity
across graduation, the exact identities (E2, E3, E6), wallet constraints,
arm-invariant tapes and buy-side fee invariance (E4).

## Seeds

| stage | seeds |
| --- | --- |
| main (6 concentration levels), shock | 1000–1299 |
| sensitivity, linear shape | 1000–1149 |
| attack policy search (training) | 0–39 |
| attack confirmation (held out) | 5000–5199 |

Calibration used development seeds 0–15, Arm A only.

## Reproduce

```bash
research/shared_narrative/reproduce.sh
```

Or stage by stage:

```bash
python3 -m bonding_lab.shared_narrative main --out research/shared_narrative/outputs --workers 4
```

```bash
python3 -m bonding_lab.shared_narrative report --out research/shared_narrative/outputs
```

The stages are `main`, `shock`, `sensitivity`, `linear`, `spam`, `bundle`,
`wash`, `report` and `all`. `--quick` runs a few seeds as a smoke test.
