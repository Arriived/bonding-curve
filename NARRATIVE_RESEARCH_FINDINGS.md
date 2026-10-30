# Narrative consolidation: completed bounded findings

This is an off-chain synthetic study. All behavioral parameters are assumptions;
no real-market validation, demand calibration, contracts, wallets or funds are
involved. The four earlier Phase 1 documents and all preexisting research are
preserved. Results below come from completed runs, not supported CLI flags.







<!-- reviewed-summary -->
The central result is conditional, rather than a blanket rejection of consolidation.
Without attacks, C retained 1223.33 versus A's 1074.57 quote units at seven days
(+13.8%) and improved the selected winner's private depth. It also
had fewer active traders. A frozen C capture policy earned 669.83
after full exit (95% interval 557.78–772.58); a D commitment/first-exit
policy earned 1382.31 and profited in all 100 confirmation seeds.
D retained 575.05, 46.5% less than A, with no statistically resolved
retention advantage over the matched single-token batch. B's protocol-fee and
creator-fee support variants slightly reduced seven-day cohort backing.

The migration-free routing grid first has a positive lower capital interval at
assumed propensity .4, corresponding to **26.5% realized quote-weighted consent**
among reachable eligible orders. At .3 the capital interval includes zero.
That is a conditional grid result, not a universal adoption requirement or a
joint improvement in survival/activity. The full model/holding-policy uncertainty
below is larger than these seed intervals suggest.
<!-- end-reviewed-summary -->

## What actually ran

The study completed 88 distinct no-attack settings and
12 trained-policy settings on **100 paired
confirmation seeds, 10000–10099**: **10,000 worlds**,
each with 480 common latent opportunities, ten candidate identities, a 30-minute
primary election and seven days of follow-up. Operational close/delay stresses
are separately named. There were 0 confirmation exceptions.
Development used seeds 0–19 (180 pilot worlds); bounded policy search
used independent seeds 100–149 (6650 worlds). These stages are not
pooled into the confirmation sample. The exact planned/completed cells, policy
parameters and seed counts are in `analysis/completed_matrix.csv` and the frozen
plan. This is not the full earlier factorial research program. The pre-confirmation
review also preserved 4600 exported rows from an interrupted initial
policy search; those rows are not used for final selection or confirmation.

An earlier 10,000-world run is preserved separately. Review found an ownership error only in D_REFUSAL: refusing creators still committed seed cash to the platform auction. The corrected run repeats all frozen settings and the same 100 seeds. Economic parameters and policies were not retuned. The earlier runs are not additional independent observations; see correction_record.json and correction_audit.json.

| Mechanism | Implemented and executed |
| --- | --- |
| A | Ten funded independent curves; diagnostic election does not move purchases; cap, funded commitment overlays, holder and concentration comparisons |
| B | Half of protocol fees supports winner; separate authorized creator-fee 60/30/10 alternative; each has lock and literal-destruction variants, real costs and +72h unlock observations |
| C | Explicit mint authorization; reach, acceptance, rejection alternatives and voluntary net-proceeds migration; independently funded overlays and strategic policies |
| D | Uniform-price curve-batch from compatible conditional escrow; no prelaunch loser tokens; net/time-weighted commitments, lock willingness, authorization and refund stresses |
| Controls | Voluntary single-token spot, single-token batch, independent candidate batches with the same cash waiting, and spot holdings locked to close |

## Mechanical evidence and implementation limits

The high-precision reference reuses the original ledger at zero coupling; economic
runs use integer quote/claim settlement, never float permission to overspend.
Tests cover ownership, full/partial redemption, separate fees, aliases, consent,
atomic rollback, repeated claims/refunds, cancellation, expiry, no winner and
deterministic replay. Test artifacts include development failures as well as
passing gates:

| gate | tests | failures |
| --- | --- | --- |
| gate10_refusal_correction | 196 | 0 |
| gate1_mechanics | 26 | 1 |
| gate1_pass | 164 | 0 |
| gate2_behavior | 46 | 0 |
| gate2_namespace_pass | 184 | 0 |
| gate2_pass | 1 | 1 |
| gate3_attacks | 190 | 0 |
| gate4_study_ready | 192 | 0 |
| gate5_pre_pilot | 193 | 0 |
| gate6_metrics | 55 | 0 |
| gate7_batch_attribution | 194 | 0 |
| gate8_final_model | 57 | 0 |
| gate9_frozen_ready | 195 | 0 |

Arithmetic witnesses, distinct from Monte Carlo estimates: 1,000 claims have
reserve 60 and cap 110. Equal D subscribers paying 30 each receive 500 claims;
first exit pays 42.50 and leaves 17.50. A funded B purchase of 30 acquires
245.3624 claims; original holders can redeem about 84.5362 and leave only 5.4638
backing support inventory. The zero-fee ordering witness earns 100 on outlay 160.
Tight limits correctly refuse atomic conversions. Different fixed-budget paths
leave different claim-quantum dust with owners; exact world conservation still
holds. A failed initial dust assertion and a test-module namespace collision were
repaired only in new files and preserved in gate artifacts.

## Main observed outcomes

Quote values are abstract units; depth is gross privately executable sell proceeds
at 5% marginal impact. Organic activity counts funded actors in the trailing 1h,
6h and 24h windows at the respective checkpoints. Curves can retain a positive
quote while no one trades. A winner is diagnostic in A, so also inspect cohort
depth and the neutral candidate benchmark in raw results.

| name | checkpoint | cohort | winner | depth5 | active | executed | outside | unexecuted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | plus_1h | 3523.764 | 751.721 | 73.342 | 58.550 | 13175.309 | 0.000 | 1277.591 |
| A | plus_24h | 1390.346 | 274.784 | 26.840 | 12.390 | 15780.909 | 0.000 | 1384.605 |
| A | plus_7d | 1074.571 | 205.728 | 20.107 | 15.010 | 17574.219 | 0.000 | 1387.358 |
| B | plus_1h | 3533.921 | 761.661 | 74.311 | 58.550 | 13173.866 | 0.000 | 1279.035 |
| B | plus_24h | 1398.058 | 283.058 | 27.647 | 12.390 | 15777.085 | 0.000 | 1388.429 |
| B | plus_7d | 1073.974 | 205.332 | 20.069 | 15.010 | 17570.394 | 0.000 | 1391.183 |
| B_CREATOR | plus_1h | 3559.340 | 787.080 | 76.789 | 58.540 | 13171.664 | 0.000 | 1281.236 |
| B_CREATOR | plus_24h | 1419.965 | 304.759 | 29.763 | 12.370 | 15770.692 | 0.000 | 1394.822 |
| B_CREATOR | plus_7d | 1072.163 | 203.858 | 19.925 | 15.010 | 17563.466 | 0.000 | 1398.111 |
| B_DESTROY | plus_1h | 3523.764 | 751.721 | 73.342 | 58.550 | 13175.309 | 0.000 | 1277.591 |
| B_DESTROY | plus_24h | 1390.346 | 274.784 | 26.840 | 12.390 | 15780.909 | 0.000 | 1384.605 |
| B_DESTROY | plus_7d | 1074.571 | 205.728 | 20.107 | 15.010 | 17574.219 | 0.000 | 1387.358 |
| B_CREATOR_DESTROY | plus_1h | 3523.764 | 751.721 | 73.342 | 58.550 | 13175.309 | 0.000 | 1277.591 |
| B_CREATOR_DESTROY | plus_24h | 1390.346 | 274.784 | 26.840 | 12.390 | 15780.909 | 0.000 | 1384.605 |
| B_CREATOR_DESTROY | plus_7d | 1074.571 | 205.728 | 20.107 | 15.010 | 17574.219 | 0.000 | 1387.358 |
| C | plus_1h | 3824.475 | 1548.786 | 151.055 | 56.440 | 11886.634 | 604.587 | 1962.045 |
| C | plus_24h | 1677.070 | 700.933 | 68.390 | 11.000 | 13977.005 | 786.201 | 2399.047 |
| C | plus_7d | 1223.334 | 530.682 | 51.790 | 13.780 | 15471.944 | 905.128 | 2581.148 |
| D | plus_1h | 2304.175 | 2304.175 | 224.706 | 46.180 | 6479.426 | 1231.942 | 6763.505 |
| D | plus_24h | 812.448 | 812.448 | 79.262 | 7.820 | 7832.292 | 1479.993 | 7872.704 |
| D | plus_7d | 575.053 | 575.053 | 56.116 | 10.280 | 8925.730 | 1626.889 | 8428.651 |
| SINGLE_SPOT | plus_1h | 1859.301 | 1859.301 | 181.331 | 45.900 | 6294.001 | 1552.558 | 6648.359 |
| SINGLE_SPOT | plus_24h | 708.092 | 708.092 | 69.088 | 7.570 | 7552.872 | 1843.403 | 7814.158 |
| SINGLE_SPOT | plus_7d | 514.601 | 514.601 | 50.222 | 10.100 | 8555.159 | 2034.095 | 8417.460 |
| SINGLE_BATCH | plus_1h | 2264.060 | 2264.060 | 220.795 | 45.100 | 5954.746 | 1363.486 | 7161.104 |
| SINGLE_BATCH | plus_24h | 847.140 | 847.140 | 82.645 | 7.360 | 7170.739 | 1652.035 | 8368.941 |
| SINGLE_BATCH | plus_7d | 568.758 | 568.758 | 55.503 | 9.710 | 8148.658 | 1842.727 | 8996.611 |
| INDEPENDENT_BATCH | plus_1h | 3630.336 | 790.935 | 77.165 | 57.950 | 11284.638 | 476.964 | 2649.461 |
| INDEPENDENT_BATCH | plus_24h | 1299.610 | 271.922 | 26.561 | 11.930 | 13886.006 | 476.964 | 2755.706 |
| INDEPENDENT_BATCH | plus_7d | 938.907 | 205.143 | 20.050 | 14.760 | 15677.915 | 476.964 | 2759.817 |
| SPOT_LOCK | plus_1h | 4234.844 | 984.434 | 96.031 | 58.000 | 12680.065 | 0.000 | 1702.680 |
| SPOT_LOCK | plus_24h | 1604.035 | 344.143 | 33.603 | 12.120 | 15245.368 | 0.000 | 1843.288 |
| SPOT_LOCK | plus_7d | 1182.219 | 241.262 | 23.572 | 14.890 | 17031.221 | 0.000 | 1853.153 |

Seven-day paired differences versus A, with seed-bootstrap 95% intervals:

| name | metric | mean_delta | low | high |
| --- | --- | --- | --- | --- |
| B | cohort_reserve | -0.597 | -0.909 | -0.198 |
| B | winner_depth_500 | -0.039 | -0.091 | 0.032 |
| B | organic_active | 0.000 | 0.000 | 0.000 |
| C | cohort_reserve | 148.763 | 118.257 | 180.014 |
| C | winner_depth_500 | 31.683 | 28.966 | 34.724 |
| C | organic_active | -1.230 | -1.450 | -1.020 |
| D | cohort_reserve | -499.518 | -528.814 | -470.563 |
| D | winner_depth_500 | 36.009 | 32.769 | 39.258 |
| D | organic_active | -4.730 | -5.120 | -4.360 |
| B_CREATOR | cohort_reserve | -2.408 | -3.051 | -1.750 |
| B_CREATOR | winner_depth_500 | -0.182 | -0.266 | -0.092 |
| B_CREATOR | organic_active | 0.000 | 0.000 | 0.000 |
| B_DESTROY | cohort_reserve | 0.000 | 0.000 | 0.000 |
| B_DESTROY | winner_depth_500 | 0.000 | 0.000 | 0.000 |
| B_DESTROY | organic_active | 0.000 | 0.000 | 0.000 |
| B_CREATOR_DESTROY | cohort_reserve | 0.000 | 0.000 | 0.000 |
| B_CREATOR_DESTROY | winner_depth_500 | 0.000 | 0.000 | 0.000 |
| B_CREATOR_DESTROY | organic_active | 0.000 | 0.000 | 0.000 |
| SINGLE_SPOT | cohort_reserve | -559.970 | -588.952 | -531.886 |
| SINGLE_SPOT | winner_depth_500 | 30.115 | 27.131 | 33.172 |
| SINGLE_SPOT | organic_active | -4.910 | -5.330 | -4.510 |
| SINGLE_BATCH | cohort_reserve | -505.813 | -537.139 | -474.030 |
| SINGLE_BATCH | winner_depth_500 | 35.395 | 32.279 | 38.614 |
| SINGLE_BATCH | organic_active | -5.300 | -5.770 | -4.830 |
| INDEPENDENT_BATCH | cohort_reserve | -135.665 | -151.143 | -119.195 |
| INDEPENDENT_BATCH | winner_depth_500 | -0.057 | -1.965 | 2.134 |
| INDEPENDENT_BATCH | organic_active | -0.250 | -0.390 | -0.120 |
| SPOT_LOCK | cohort_reserve | 107.648 | 88.031 | 128.662 |
| SPOT_LOCK | winner_depth_500 | 3.465 | 1.776 | 5.452 |
| SPOT_LOCK | organic_active | -0.120 | -0.200 | -0.050 |

The key retention comparisons, including matched batch controls, are:

- B versus A: seven-day cohort reserve difference -0.597, 95% interval [-0.909, -0.198].
- C versus A: seven-day cohort reserve difference +148.763, 95% interval [+118.257, +180.014].
- D versus A: seven-day cohort reserve difference -499.518, 95% interval [-528.814, -470.563].
- D versus INDEPENDENT_BATCH: seven-day cohort reserve difference -363.854, 95% interval [-394.393, -333.396].
- D versus SINGLE_BATCH: seven-day cohort reserve difference +6.295, 95% interval [-9.473, +21.802].

The strongest favorable evidence is any positive absolute winner depth/retention
entry in these tables. The strongest contrary evidence is loss of whole-cohort
capital or activity, loss of an effect against the batch/lock controls, or gains
that disappear after support unlock. These quantities are shown together so an
increased winner share cannot substitute for a capital gain.

Election accuracy against the evaluator-only latent-offer benchmark (a limited
synthetic benchmark, not knowledge of genuine people) is:

| name | correct_future_choice | winner_undefined | organic_mean_events | creator_cash_change |
| --- | --- | --- | --- | --- |
| A | 0.340 | 0.000 | 24.920 | -57.622 |
| A_COMMIT | 0.350 | 0.270 | 24.920 | -57.622 |
| A_HHI | 0.220 | 0.000 | 24.920 | -57.622 |
| A_HOLDERS | 0.250 | 0.020 | 24.920 | -57.622 |
| A_TIMECOMMIT | 0.350 | 0.270 | 24.920 | -57.622 |
| B | 0.340 | 0.000 | 24.920 | -57.549 |
| B_CREATOR | 0.340 | 0.000 | 24.920 | -125.349 |
| B_CREATOR_DESTROY | 0.340 | 0.000 | 24.920 | -125.441 |
| B_DESTROY | 0.340 | 0.000 | 24.920 | -57.575 |
| C | 0.340 | 0.000 | 22.230 | -65.486 |
| C_COMMIT | 0.350 | 0.270 | 22.380 | -62.924 |
| C_HHI | 0.220 | 0.000 | 22.350 | -65.370 |
| C_HOLDERS | 0.250 | 0.020 | 22.450 | -65.212 |
| C_TIMECOMMIT | 0.350 | 0.270 | 22.380 | -62.924 |
| D | 0.310 | 0.000 | 16.010 | -107.793 |
| D_TIME | 0.320 | 0.000 | 15.820 | -108.216 |
| INDEPENDENT_BATCH | 0.310 | 0.000 | 24.550 | -66.253 |
| SINGLE_BATCH | 0.100 | 0.000 | 14.770 | -112.418 |
| SINGLE_SPOT | 0.100 | 0.000 | 15.370 | -20.367 |
| SPOT_LOCK | 0.290 | 0.000 | 24.740 | -61.189 |

The primary variants have zero extra attention from winning. Positive and negative
attention sensitivities are separate cells, not evidence that an election creates
organic attention. All starting quote is 39,100 in each world, including the
funded attacker, unused capital and sponsor. No rejected budget regenerates cash.
Outside reserves remain accounted but are excluded from platform/cohort retention.

## Conditional acceptance and participation

In the migration-free routing grid, the smallest tested assumed propensity with a strictly positive lower interval for cohort retention is 0.4. This is conditional on reach=.6 and the stated rejection behavior; it is not a universal threshold. The second grid includes migration=.25 and cannot attribute its effect solely to routing.

| grid | assumed_acceptance | realized_quote_acceptance | capital_delta | low | high |
| --- | --- | --- | --- | --- | --- |
| with_migration | 0.000 | 0.000 | 116.242 | 77.667 | 153.098 |
| routing_only | 0.000 | 0.000 | -98.688 | -120.655 | -77.667 |
| routing_only | 0.100 | 0.063 | -60.761 | -83.517 | -38.402 |
| with_migration | 0.100 | 0.061 | 123.157 | 87.264 | 162.238 |
| with_migration | 0.200 | 0.128 | 131.309 | 97.414 | 166.725 |
| routing_only | 0.200 | 0.132 | -29.588 | -52.152 | -7.237 |
| routing_only | 0.300 | 0.202 | 4.834 | -18.331 | 27.862 |
| with_migration | 0.300 | 0.197 | 139.477 | 105.731 | 172.220 |
| with_migration | 0.400 | 0.261 | 143.439 | 112.264 | 175.919 |
| routing_only | 0.400 | 0.265 | 28.626 | 4.579 | 50.776 |
| routing_only | 0.500 | 0.328 | 46.247 | 22.055 | 68.614 |
| with_migration | 0.500 | 0.322 | 148.336 | 117.184 | 179.325 |
| routing_only | 0.600 | 0.390 | 66.268 | 43.279 | 88.355 |
| with_migration | 0.600 | 0.383 | 148.763 | 118.257 | 180.014 |
| with_migration | 0.700 | 0.446 | 150.297 | 119.591 | 180.738 |
| routing_only | 0.700 | 0.453 | 81.437 | 57.049 | 103.920 |
| with_migration | 0.800 | 0.511 | 151.186 | 122.857 | 179.076 |
| routing_only | 0.800 | 0.519 | 96.377 | 72.259 | 119.911 |
| routing_only | 0.900 | 0.583 | 106.477 | 82.816 | 129.445 |
| with_migration | 0.900 | 0.575 | 150.065 | 122.729 | 177.113 |
| with_migration | 1.000 | 0.640 | 152.448 | 124.051 | 180.125 |
| routing_only | 1.000 | 0.648 | 117.126 | 93.895 | 140.258 |

Assumed propensity is reduced by loyalty and price, so 1 does not mean universal
consent. Reach controls whether a loser-page order encounters the router at all.
`C_REACH_*`, `C_REJECT_*`, `C_MIGRATE_*`, `D_BROAD_*` and `D_LOCK_*` cells isolate
those assumptions. D's cash-lock willingness and allowed-winner choice are
different decisions from C's post-election consent. One-factor sweeps do not
establish a universal joint adoption threshold. All distributions and paired
differences, including no-benefit settings, are exported rather than selected
only for favorable averages.

## Unlocks, controls and interpretation

| name | label | cohort_reserve | winner_reserve | support_claims | support_cash | support_unlock_proceeds |
| --- | --- | --- | --- | --- | --- | --- |
| B | after_unlock | 1044.683 | 197.439 | 0.000 | 9.389 | 9.064 |
| B | before_unlock | 1053.794 | 206.550 | 48.696 | 0.324 | 0.000 |
| B_CREATOR | after_unlock | 1039.674 | 192.998 | 0.000 | 34.749 | 32.793 |
| B_CREATOR | before_unlock | 1072.609 | 225.933 | 171.825 | 1.956 | 0.000 |
| B_CREATOR_DESTROY | after_unlock | 1046.213 | 198.896 | 0.000 | 1.949 | 0.000 |
| B_CREATOR_DESTROY | before_unlock | 1046.213 | 198.896 | 0.000 | 1.949 | 0.000 |
| B_DESTROY | after_unlock | 1046.213 | 198.896 | 0.000 | 0.324 | 0.000 |
| B_DESTROY | before_unlock | 1046.213 | 198.896 | 0.000 | 0.324 | 0.000 |

B's purchased claims and actual fee cash have explicit owners. Locking is a
temporary restriction on selling; destruction leaves a separately reported
inaccessible buffer. Neither is permanent LP capital. The before/after-unlock
drop measures the withdrawal option that a locked snapshot conceals. Fee support
can pay earlier holders, as the exact witness demonstrates.

D is compared to independent batches and a voluntary single-token batch in the
paired table, holding the batch curve and pre-close cash waiting explicit. Any
gain against ten spot markets must survive those controls before it can be
attributed to narrative selection. Choosing a more popular candidate, restricting
available assets, batching entry prices and forcing cash to wait are distinct
causal changes. The controls do not identify a real-world equilibrium.

## Strategic attacks

Every macro policy has one 5,000-unit actor endowment across aliases. The bounded
search includes abstention, funded capture/dump sizes and exit times, wallet splits,
wash rounds, and predictable B-epoch frontruns. D searches funded commitments and
immediate/one-hour exits. Policies were optimized independently against A and the
other selected architectures; abstaining families create no duplicate confirmation
samples. Actor identities aggregate evaluation budgets only; public elections see
addresses. Fee/holder/concentration metrics can therefore be misleading.

| name | mean_profit | low | high | profit_frequency | mean_peak | mean_fees | mean_other_trader_loss | complete_exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATTACK_A_capture | -11.351 | -25.654 | 2.509 | 0.390 | 250.000 | 1.974 | -9.598 | 100 |
| ATTACK_B_capture | -11.290 | -25.326 | 2.075 | 0.390 | 250.000 | 1.975 | -9.683 | 100 |
| ATTACK_C_capture | 669.832 | 557.781 | 772.576 | 0.890 | 3000.000 | 26.710 | 696.972 | 100 |
| ATTACK_C_split | 673.904 | 570.415 | 775.331 | 0.890 | 2999.998 | 27.987 | 701.669 | 100 |
| ATTACK_D_capture | 1382.313 | 1358.752 | 1405.293 | 1.000 | 3000.000 | 29.562 | 1390.364 | 100 |
| ATTACK_B_CREATOR_capture | -11.025 | -24.546 | 3.866 | 0.390 | 250.000 | 1.976 | -9.790 | 100 |
| ATTACK_D_TIME_capture | 1006.110 | 882.117 | 1122.781 | 0.730 | 3000.000 | 21.568 | 1012.548 | 100 |
| ATTACK_A_HOLDERS_capture | -11.351 | -25.340 | 3.166 | 0.390 | 250.000 | 1.974 | -9.598 | 100 |
| ATTACK_C_HOLDERS_capture | -25.099 | -37.869 | -12.433 | 0.340 | 250.000 | 1.919 | -23.677 | 100 |
| ATTACK_C_HOLDERS_split | 673.904 | 569.570 | 775.862 | 0.890 | 2999.998 | 27.987 | 706.357 | 100 |
| ATTACK_C_HHI_capture | 8.079 | 2.154 | 13.876 | 0.590 | 250.000 | 2.052 | 9.686 | 100 |
| ATTACK_C_HHI_split | 663.878 | 557.136 | 768.873 | 0.890 | 2999.998 | 27.947 | 695.065 | 100 |

Profit frequency counts positive cash P&L with zero residual inventory. The full
table includes Wilson intervals, extrema, capital-days and a separately reported
10% annual opportunity-cost diagnostic. Peak recoverable funding is distinct from
irreversible fees. Other-trader losses are paired against the same mechanism
without that policy; a profitable trade also available in A is not automatically
a new consolidation exploit. A failure to find profit is only a finite search
result. Search spaces omit strategic borrowing, coalitions among unrelated actors,
creator-side bribes and general equilibrium entry.

Separately, the 56-cell known-order grid optimizes funded migration frontruns
against output limits and actual fee costs. Selected fee-bearing profitable cases:

| slippage_bps | budget | peak_funding | irreversible_fees | complete_exit_profit | filled |
| --- | --- | --- | --- | --- | --- |
| 5000 | 1000 | 1000.000 | 12.454 | 1104.069 | True |
| 5000 | 500 | 500.000 | 7.395 | 840.290 | True |
| 5000 | 250 | 250.000 | 4.387 | 589.332 | True |
| 5000 | 100 | 100.000 | 2.128 | 325.601 | True |

Identical known purchases in the A control produce the same ordering profit.
Routing and visible migrations concentrate opportunities; independent curves do
not remove same-token MEV. Tight zero-slippage cases refuse/roll back both
conversion legs, and the attacker still pays its own round trip. Primary D has no
prelaunch secondary winner market: such price manipulation is N/A before issuance;
its relevant attack is capital capture followed by first exit.

## Honest recommendation and plain English

**A: go as the research control.** It preserves asset choice and isolates the
costs and benefits of consolidation. This is not a recommendation to launch or
invest in memecoins. Its independent markets still have adverse selection and
ordering risk.

**B: no-go as a claimed durable liquidity innovation.** It recycles already paid
fees and changes who can sell into them. A larger winner position during a lock
does not establish improved cohort retention, private depth or organic survival.
The creator-fee variant also redirects losing creators' income; adoption is
unproven. It could be studied as an explicitly priced promotional expense, with
ownership/unlock disclosure and the measured costs accepted.

**C: conditional research only; no-go for an established superiority claim.**
It implements voluntary routing without confiscating loser reserves, but retention
depends on reach, actual acceptance, abandonment, prices and later selling.
Changing the token received creates no external capital. No universal acceptance
threshold or creator adoption estimate follows from these synthetic runs.

**D: no-go in this initial form without addressing allocation/exit incentives.**
Its batch allocation is mechanically funded, but equal average-price entry into
an increasing redeemable curve rewards the first seller at other subscribers'
expense. Cash waiting and concentration must be distinguished from better
organic demand. The adverse arithmetic and trained commitment/exit strategies
cannot be rescued by a high initial market cap.

In simple English: putting money behind one name can make that name look stronger.
It does not create more money or guarantee that buyers want it. Some buyers leave;
early holders can sell into the redirected purchases; batch subscribers can race
to withdraw before one another. The useful product hypothesis left open is better
discovery and voluntary execution, with costs and refusal visible—not a demonstrated
economic gain from electing a canonical coin.

## Reproduction and evidence

Run from the repository root using the existing environment. Choose a **new study
directory** for reruns and capture a new preservation inventory before starting.
The supplied completed bundle is `research/narrative_consolidation/bounded_study/corrected_v2`.
First run `python -m bonding_lab.narrative init --root <new-study-directory>` to
capture the new preservation inventory. Reports are saved inside the study;
an existing top-level findings report is never overwritten by a reproduction.

```powershell
.\.venv\Scripts\python.exe -m bonding_lab.narrative pilot --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative train --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative freeze --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative confirm --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative report --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative verify --root <study-directory>
```

The frozen plan hashes source and configurations before confirmation. Confirmation
stores all 100 common tapes, every seed/checkpoint result, representative complete
financial traces and terminal wallets for seed 10000 in every treatment, ranking
records, source snapshots, progress/failure records and completion manifests.
Other traces are reproducible with `python -m bonding_lab.narrative replay
--root <study-directory> --name C --seed 10037 --out <new-replay-directory>`;
replay verifies the exact stored outcome hash. They are not claimed already
exported. Bootstrap intervals describe seed variation
inside this model, not uncertainty about human behavior or real adoption. The
current API discovery snapshots from Phase 1 are not a calibration dataset.

<!-- supplemental-findings -->
## Additional holding-policy audit: exploratory, 200 worlds

The primary agent policy attaches sell intentions to the mint actually purchased.
After voluntary migration, an original loser-mint sell intention can therefore
become ineffective; winner inventory can be sold on later winner-mint intentions
or terminal exit. This is an uncalibrated holding-policy assumption, not a legal
lock or permanent LP capital. It can inflate the apparent persistence of migrated
backing. The migration-free acceptance grid avoids that particular channel.

An additional, explicitly exploratory check carries those existing sell intentions
forward to the received winner after conversion. It uses the same 100 tapes and
frozen economic settings for C without attack and with its already-trained capture
policy: 200 extra worlds, no retraining or replacement of the preregistered matrix.
It is model-sensitivity evidence, not another independent confirmation sample.

| name | metric | original_mean | continuity_mean | mean_delta | low | high |
| --- | --- | --- | --- | --- | --- | --- |
| C | cohort_reserve | 1223.334 | 1118.814 | -104.520 | -121.321 | -87.996 |
| C | winner_depth_500 | 51.790 | 39.890 | -11.901 | -13.629 | -10.288 |
| C | organic_active | 13.780 | 13.960 | 0.180 | 0.100 | 0.260 |
| C | attacker_cash_pnl | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| ATTACK_C_capture | cohort_reserve | 1260.374 | 1159.265 | -101.109 | -115.944 | -86.657 |
| ATTACK_C_capture | winner_depth_500 | 46.481 | 34.719 | -11.761 | -13.274 | -10.274 |
| ATTACK_C_capture | organic_active | 13.540 | 13.740 | 0.200 | 0.110 | 0.300 |
| ATTACK_C_capture | attacker_cash_pnl | 669.832 | 398.572 | -271.260 | -304.309 | -238.802 |

Under sell-intent continuity, C's cohort gain versus A falls to 44.24
(95% paired interval [19.75, 70.11]), from the primary gain of 148.76.
The unchanged capture policy still earns 398.57 on average after complete exit
(interval [299.08, 499.01]). Thus the favorable capital result is sensitive
to agent holding rules, while profitable capture survives this alternative.
This materially limits a favorable interpretation of C's primary reserve result.

Reproduce the extra check and appendix, after generating the main report:

```powershell
.\.venv\Scripts\python.exe research/narrative_consolidation/bounded_study/corrected_v2/migration_exit_sensitivity.py
.\.venv\Scripts\python.exe research/narrative_consolidation/bounded_study/corrected_v2/augment_findings.py
```

The sensitivity script requires a new output directory if it has already run;
its saved `runs.csv.gz`, `paired_effects.csv` and manifest are the completed evidence.
All 196 main implementation tests pass; all 9,900 worlds outside the repaired
D refusal case match the preserved first run exactly. The earlier 10,000 worlds
are retained, not pooled to claim 200 independent confirmation seeds.

## Revenue and participant cash after feasible exits

| name | protocol_and_support_quote | gross_protocol_fees | gross_creator_fees | trader_cash_change | creator_cash_change | network_quote |
| --- | --- | --- | --- | --- | --- | --- |
| A | 45.201 | 35.201 | 105.602 | -303.657 | 200.599 | 7.852 |
| B | 38.585 | 35.225 | 105.673 | -297.089 | 200.589 | 7.910 |
| B_CREATOR | 89.477 | 35.292 | 105.876 | -279.959 | 132.569 | 7.908 |
| C | 44.531 | 34.531 | 103.593 | -305.886 | 198.220 | 7.723 |
| D | 31.218 | 21.218 | 63.652 | -31.795 | -63.300 | 4.166 |

Protocol/support cash includes launch receipts and cash remaining in the named
fund; gross fee accrual counts each actual trade, including support trades, and
is not additional external capital. Creator and trader cash changes use their
own funded initial balances. Network and outside-market accounts remain in world
conservation. Residual unprofitable-to-redeem claim dust is exported separately.
The table is a cash distribution, not a proof that fee revenue benefits traders.

There is favorable counterevidence to a blanket negative judgment: without an
attacker, D's mean trader cash loss is only 31.80
versus A's 303.66. B also
reduces trader cash losses modestly by transferring fee value away from its
other beneficiaries. These outcomes coexist with lower D trading/participation
and different creator cash outcomes; they are not proof of improved total welfare
or permanent liquidity. D's trained attack imposes roughly 1390.36
additional trader loss relative to its no-attack world. No architecture is best
on every measured dimension under equal starting money.

## Decision and open questions

Retain A as the experimental control. Reject B as a demonstrated durable-liquidity
improvement and D's current allocation/exit design. C merits further controlled
research only: there is a measured conditional reserve/depth benefit, but lower
activity, profitable strategic capture and sensitivity to holding behavior prevent
a launch recommendation. Net commitment and time weighting both permit profitable
D capture; time weighting reduces the measured reward in this policy class but
does not establish a manipulation-resistant winner rule. Address concentration
penalties remain vulnerable to actor-controlled splits.

Losing C holders keep their original claims unless they authorize conversion;
D's incompatible subscribers refund. Creator adoption remains unknown: refusal
is an exogenous stress here, not an equilibrium participation estimate. The study
does not establish an added organic-attention effect, real human acceptance,
permanent liquidity, seven-day real-market survival, or a defensible moat.
Reject a broad production claim if it relies on ignoring abandonment, locked or
unclaimed money, the migration holding-policy effect, or attacks funded within
the tested 5,000-unit budget.
