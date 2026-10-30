# Corrected bounded study

This is the authoritative corrected bundle. `confirmation/manifest.json` records
completion. The parent bundle preserves the first 10,000-world run; its D creator
refusal stress still committed refusing creators' seed capital to platform
escrow. That participation-rule bug is repaired here and covered by a new test.
The complete suite passed 196 tests (138 existing, 58 new).

All 100 frozen target configurations/policies and seeds 10000–10099 are identical
to the first run. The whole matrix is repeated, with new source hashes and traces.
`correction_audit.json` checks that all 9,900 worlds outside `D_REFUSAL` have
exactly the same outcome hashes. This is an implementation repair, with no
behavioral parameter or attack-policy tuning on confirmation outcomes.

Read `NARRATIVE_RESEARCH_FINDINGS.md`, `IMPLEMENTATION.md` and
`analysis/completed_matrix.csv`. `correction_record.json` identifies the earlier
bundle; `audit_confirmation.py` verifies the repair and all tape hashes. The
parent README contains the full CLI reproduction sequence. Use this root for
final report, replay and preservation commands:

```powershell
.\.venv\Scripts\python.exe -m bonding_lab.narrative report --root research/narrative_consolidation/bounded_study/corrected_v2
.\.venv\Scripts\python.exe research/narrative_consolidation/bounded_study/corrected_v2/audit_confirmation.py
.\.venv\Scripts\python.exe -m bonding_lab.narrative replay --root research/narrative_consolidation/bounded_study/corrected_v2 --name C --seed 10037 --out research/narrative_consolidation/replay_C_10037
.\.venv\Scripts\python.exe -m bonding_lab.narrative verify --root research/narrative_consolidation/bounded_study/corrected_v2
```

The original 465-file preservation inventory remains in the parent bundle. The
corrected run also captures 756 pre-revision files, including the first run's
evidence and the corrected implementation, before generating this bundle.

## Data dictionary qualifications

Quote amounts use abstract units. `offered` is wallet-funded budget after the
synthetic attention decision, before routing; the complete common latent budgets
are in the tapes. `reachable` counts eligible loser-directed budgets encountering
C; `authorized` records actual synthetic consent, and `routed_executed` records
the resulting paid fills. Price/participation decisions may still prevent a fill
after consent. Counts and quote-weighted acceptance are distinct.

`abandoned_unexecuted` is foregone order flow, not cash destruction or a user
loss. Returned auction money can fund a later opportunity because it remains
owned cash; it is not a new endowment. `cohort_reserve` excludes outside markets
and inaccessible destruction buffers. Add the separately reported buffer to
redeemable backing to reconstruct total physical market cash. Locked support
claims are owned inventory, excluded from private sell-depth during the lock.

Funded organic activity excludes scheduled support and actor attacks. At +1h,
+24h and +7d its trailing windows are 1h, 6h and 24h. Feasible forced exits occur
after those checkpoints and have their own label. Trader cash P&L before complete
exit must be read alongside residual holdings; first-exit marks are not collective
liquidation proceeds. Actor capital-days are a cash-deployment diagnostic that
includes unrecovered fees, not a collateral appraisal.

All human behavior, grouping, elasticity and creator refusal parameters are
synthetic. No real-market causal validation or identity oracle is claimed.

The completed primary matrix contains 10,000 worlds and 90,000 checkpoint rows.
An explicitly exploratory holding-policy check adds 200 worlds on the same 100
paired tapes: `migration_exit_sensitivity.py` carries original sale intentions
forward after conversion. `augment_findings.py` appends its measured effects and
the reviewed interpretation to the findings without changing the frozen primary
results. Run it after the main report and the sensitivity; completed outputs are
under `exit_continuity_sensitivity/`. These are not extra independent seeds.

Three additional exact-hash replays are saved as `replay_C_10037/`,
`replay_D_10073/` and `replay_D_REFUSAL_10042/`. The correction audit confirms
9,900 unchanged worlds and exactly 100 changed refusal-case worlds. Final report
hashes and the supplemental run count are in `reviewed_findings_manifest.json`.
