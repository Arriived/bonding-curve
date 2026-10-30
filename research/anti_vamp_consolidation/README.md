# Anti-vamp research package

Start with the root [goal and complete findings](../../ANTI_VAMP_RESEARCH.md). The current objective is one meme's early attention and liquidity concentrating around a clearly identified original/canonical mint, while allowing open token creation.

This directory preserves the full follow-up research from the conversation. The two older per-study ZIP files are unpacked here rather than duplicated. The source snapshots, prior development versions, reports, and evidence remain byte-identical.

| Path | Contents |
| --- | --- |
| `outputs/ANTI_VAMP_FINDINGS.md` | Main one-original-plus-copies launch-hour study |
| `outputs/anti_vamp_study/` | 11,700 confirmation worlds, minute flows, plans, trained policies, source, tests, exact replays, preservation checks |
| `outputs/C_PERMISSIONLESS_FINDINGS.md` | Earlier open-entry C study, including selling-policy audit |
| `outputs/c_permissionless_study/` | 5,600 confirmation worlds, 1,200 exploratory holding-policy worlds, controls, source, tests, and traces |
| `outputs/PHASE2_GO_NO_GO_REVIEW.md` | Earlier read-only Phase 1 assessment |
| `outputs/CODEX_PHASE2_IMPLEMENTATION_BRIEF.md` | Earlier implementation brief |
| `outputs/REVIEW_EVIDENCE.json` | Hash and arithmetic review evidence |
| `work/` | Exact runnable study and historical reporting scripts |
| `interface/open-launch-preview.html` | Standalone earlier UI concept; open locally in a browser |
| `interface/open-launch-consolidation.html` | Original fragment used by the conversation visualization |
| `interface/*.png` | Previously verified wide and narrow previews |
| `PACKAGE_MANIFEST.json` | SHA-256 inventory of every file in this directory except itself |

## Verify the saved evidence

From the repository root run:

```powershell
python -B research/anti_vamp_consolidation/verify_package.py
python -B -m unittest discover -s research/anti_vamp_consolidation/work/anti_vamp -p test_model.py -v
python -B -m unittest discover -s research/anti_vamp_consolidation/work/c_followup -p test_open_model.py -v
```

The unittest suites require NumPy and pandas from the project environment. The verifier uses only the Python standard library. It checks file hashes, frozen model source, report hashes, confirmation completion, seed sets, row counts, and recorded exact replays; it does not rerun all economic worlds.

## Reproduce the anti-vamp economic experiment

Do this in a **fresh scratch directory**, keeping the relative `work/` and `outputs/` layout. Do not overwrite the archived completed outputs. Copy `work/anti_vamp/` and `work/select_anti_vamp_copy_families.py` there. Then run:

```powershell
python -B -m unittest discover -s work/anti_vamp -p test_model.py -v
python -B work/anti_vamp/study.py init
python -B work/anti_vamp/study.py pilot
python -B work/anti_vamp/study.py train
python -B work/select_anti_vamp_copy_families.py
python -B work/anti_vamp/study.py confirm
python -B work/anti_vamp/study.py analyze
```

The helper between training and confirmation is required: it freezes separate copy-only selections from the already completed training grid. It must precede confirmation. Full confirmation is a substantial CPU run. The stored bundle already contains all completed results.

For the earlier open-launch study, follow `outputs/C_PERMISSIONLESS_FINDINGS.md`. Its preservation inventory uses the original machine's repository path. On another machine that read-only path must be adjusted before predeclaration, producing a new source hash. Historical report/audit scripts also contain local paths. They are preserved for provenance, not presented as portable tools. `work/check_mockup.cjs` similarly records the original local browser/runtime paths.

The main model is an integer, independently funded linear curve. It does not simulate Pump's actual virtual reserves, graduation, or a live launchpad. Launch fees and human choices are synthetic assumptions. The earlier interface uses an elected lead; canonical assignment remains an unresolved product dependency.

## Publication scope

Publication adds these reports and research artifacts. Earlier preservation records remain historical records of experiments that did not modify the original project. They do not claim that this later authorized addition never happened.
