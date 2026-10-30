# C on an open launchpad: completed follow-up

30 October 2026. Synthetic, off-chain research. No deployment, wallet use, real funds, or empirical adoption calibration.

## Decision in plain English

Permissionless creation and optional consolidation can be separate layers. Anyone can create an independent coin; one narrative page gathers discovery, and a fresh buyer may explicitly choose its current lead. The platform cannot redirect third-party purchases or move existing holder collateral without authorization.

The fresh-seed base comparison changes seven-day whole-narrative backing from 800.61 in A to 858.07 in C: 57.46 (+7.2%), with a 95% paired seed-bootstrap interval [37.50, 77.00]. This is routing only: holder migration is disabled throughout this extension. It is a conditional model result, not a real-market forecast.

The safeguards and open-entry stresses below test both the possible benefit and the capture costs. Interpret attack profits against independently trained A and the same-policy A controls; ordinary early trading can also be profitable in A.

## What actually ran

- 21 matched environments, each with A and C: 4,200 no-active-trading-attack confirmation worlds.
- Eight independently selected policy targets: 800 trained-policy confirmation worlds.
- Six additional A controls receiving the exact frozen C policy: 600 worlds.
- Total: **5,600 confirmation worlds**, **100 fresh paired seeds 30000–30099**, and **22,400 checkpoint/terminal rows**.
- Development: 40 pilot worlds on seeds 2000–2004. Attack training: 3,200 worlds on separate seeds 200–219, using 20 candidate strategies per target. Development and training do not increase the confirmation sample size.
- All settings and the policy class were written before confirmation. Attack choices were frozen after training. Confirmation source hashes are enforced. There was no outcome-dependent early stopping or retuning.
- Eighteen new implementation tests passed. An expiry-boundary bug was found and corrected before predeclaration; the development record identifies it. The existing repository suite was not rerun because its code was copied read-only and never changed.
- Three arbitrary stored worlds replay with exact output hashes. Integer conservation and ownership assertions run at every observation and terminal checkpoint.

The primary prespecified contrast is base C versus matched A for seven-day backing. All other intervals are exploratory; there is no multiple-comparison-adjusted claim that every favorable cell will generalize. Sampling intervals omit uncertainty about real human behavior.

## Model and permissionless boundaries

The experiment uses an isolated copy of the previous integer independent-curve ledger, not modifications to the original repository. The curve remains a=.01 and b=.0001, quote quantum 10^-6, claim quantum 10^-4. It does not reproduce Pump's virtual-reserve formula or graduation into an AMM.

Every world has 39,100 quote units: 32,000 across 64 traders, 2,000 across ten original creators, 5,000 for the coordinated actor, and 100 for a sponsor. There are 480 common latent opportunities and the same original trader budgets across matched worlds. Extra mints create no additional money or opportunities. Sales and refunds reuse owned cash; no external replenishment occurs.

There is no platform launch fee in the base case and no mandatory creator purchase. Each launch incurs a synthetic .01 network payment and .02 account deposit, paid by the creator or attacker. The sponsorship sensitivity pays those costs from the same finite 100-unit sponsor. Deposits remain separately named cash accounts; no recoverability or token-market backing is assumed within the observation horizon. Cash P&L excludes them. These are abstract research costs, not current SOL conversions.

Ten original creators can launch externally in the outside-creator stress. Whole-narrative backing includes their markets, preventing an apparent gain from simply dropping refused creators from the denominator. Platform-only and all-market backing, including the separate outside alternative, are also exported. Fees earned by attacker-created mints are credited to the same real actor, including self-payments; they are not new capital.

The 10/90-spam settings have 20/100 total possible mints. The spam count is an exogenously declared stress; it is not an estimate of equilibrium launch supply. Creating more mints uses the actor's existing budget. Half the arrivals in the raw-feed stress receive equal per-live-mint discovery exposure; this is an explicit naive-feed assumption. The grouped-intentions setting removes that per-mint discovery lottery and preserves incoming preferences, without minting more demand. It does not validate a semantic classifier or prove a real grouped interface raises attention.

Late mints can launch and trade after close. They cannot reopen the fixed thirty-minute election. A fresh buyer can still explicitly choose the incumbent from a late entrant's native entry point. No existing position is converted. Multi-round leader changes, legitimate new entrants bringing fresh audiences, classifier false positives, and a creator participation equilibrium remain unimplemented.

The base acceptance ceiling is .6 and reach is .6. Loyalty and price reduce actual synthetic consent. Rejected buyers choose the preferred asset with probability .5, the outside alternative with probability .25, or retain cash otherwise. These are assumptions, not measured preferences. Directly choosing a mint and accepting a recommendation are different orders. Zero-reach and zero-acceptance-with-direct-fallback controls are covered by implementation tests.

The `active` count includes funded organic fills in any modeled market, including the outside alternative, over trailing 1h/6h/24h windows. It is not platform-only activity. Seven-day timestamps do not establish seven-day real-market survival.

## Retained backing at seven days

| Environment | A backing | C backing | C−A | 95% paired interval | Relative mean change |
| --- | --- | --- | --- | --- | --- |
| Free launch; routing only | 800.61 | 858.07 | 57.46 | [37.50, 77.00] | +7.2% |
| 10 additional spam mints | 1,620.37 | 1,455.74 | -164.64 | [-191.89, -139.13] | -10.2% |
| 90 additional spam mints | 2,519.72 | 2,094.48 | -425.24 | [-457.26, -394.32] | -16.9% |
| 90 late spam mints | 1,384.17 | 1,180.78 | -203.39 | [-229.37, -178.80] | -14.7% |
| 20% router reach | 800.61 | 833.54 | 32.93 | [21.01, 43.74] | +4.1% |
| 50% creator outside probability | 800.61 | 834.72 | 34.11 | [19.46, 50.50] | +4.3% |
| Low acceptance ceiling | 800.61 | 776.86 | -23.75 | [-39.64, -7.09] | -3.0% |
| 90 spam; grouped incoming intentions | 800.61 | 858.07 | 57.46 | [37.57, 77.96] | +7.2% |
| 1.25% underlying trading fees | 794.03 | 850.77 | 56.75 | [36.87, 78.17] | +7.1% |
| Additional 0.45% router fee | 800.61 | 857.29 | 56.68 | [36.75, 75.86] | +7.1% |
| Daily routing budget | 800.61 | 793.04 | -7.57 | [-23.41, 7.52] | -0.9% |
| Six-hour expiry | 800.61 | 888.95 | 88.34 | [74.70, 101.84] | +11.0% |
| Time-weighted cap and minimum age | 800.61 | 854.93 | 54.32 | [33.02, 74.77] | +6.8% |
| Relative-price limit | 800.61 | 815.99 | 15.38 | [-2.07, 32.84] | +1.9% |
| Combined safeguards | 800.61 | 824.63 | 24.02 | [16.32, 32.07] | +3.0% |
| Combined safeguards with 90 spam | 2,519.72 | 2,396.75 | -122.97 | [-139.13, -106.28] | -4.9% |

Relative changes are ratios of mean differences to mean A backing. Confidence intervals are in quote units. The curve shape is identical within every matched pair. All results are after normal scheduled sells and before forced diagnostic terminal exits.

In the base case, 5%-impact winner sell depth changes from 16.81 to 36.34. Its paired difference is 19.53 [17.57, 21.68]. Funded active-trader count across all modeled markets changes from 15.62 to 14.73. These measures answer different questions from whole-narrative backing.

## Strategic capture

Policies vary an actor-funded purchase budget of 250/1,000/3,000, purchase at 5%/85% of the contest window, and exit at finalization/one hour/six hours after finalization. Abstention and a 32-wallet split are included, for 20 candidates per target. The actor has 5,000 total across all aliases. In spam settings the same actor also pays launch costs and collects its mints' actual creator fees.

Training maximizes terminal cash P&L within this disclosed class; selected policies must fully exit token inventory in training. Both A and C are optimized separately for the base and 90-spam environments. Guarded C policies are also evaluated against A with the very same settings, size, timing, and exits. This is a bounded search, not a proof of a globally optimal attack.

| Environment | Model | Total actor cash P&L | Idle actor P&L | Added P&L vs idle | 95% interval for added P&L | Positive cash P&L | Peak deployed cash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | A | 260.25 | 0.00 | 260.25 | [207.85, 311.34] | 85% | 1,000.00 |
| base | C | 767.91 | 0.00 | 767.91 | [686.48, 844.45] | 95% | 3,000.00 |
| spam90 | A | 49.18 | 46.48 | 2.70 | [-2.46, 8.01] | 99% | 110.25 |
| spam90 | C | 675.89 | 32.01 | 643.87 | [593.91, 695.01] | 99% | 2,986.43 |
| daily_cap | C | 626.55 | 0.00 | 626.55 | [544.74, 705.10] | 93% | 3,000.00 |
| timecap | C | 767.91 | 0.00 | 767.91 | [683.66, 848.22] | 95% | 3,000.00 |
| combined | C | 369.65 | 0.00 | 369.65 | [319.86, 420.24] | 93% | 1,000.00 |
| combined90 | C | 59.52 | 41.79 | 17.73 | [6.62, 30.22] | 99% | 110.25 |

“Idle” in a spam environment means no active trading attack, but the exogenous spam launches still occur and can earn creator fees. Thus total actor profit alone is not the incremental benefit of a capture trade. The added-P&L column controls for that income and launch expense. All token-exit residuals are exported; an inaccessible account deposit is not counted as realized cash or a market reserve.

### Exact C-policy comparison against A

| C environment | C actor P&L | A with identical policy | Additional P&L in C | 95% paired interval |
| --- | --- | --- | --- | --- |
| base | 767.91 | 218.29 | 549.62 | [513.99, 586.02] |
| spam90 | 675.89 | 9.28 | 666.60 | [625.44, 704.61] |
| daily_cap | 626.55 | 218.29 | 408.26 | [382.58, 435.19] |
| timecap | 767.91 | 218.29 | 549.62 | [509.83, 586.18] |
| combined | 369.65 | 260.25 | 109.40 | [93.80, 125.96] |
| combined90 | 59.52 | 49.18 | 10.34 | [1.70, 20.31] |

These are the appropriate within-policy comparisons for routing-amplified profit. An independently optimized A result remains a complementary check. Participant cash outcomes and attacker-induced trader losses are in `attacks.csv`; profit frequencies describe synthetic seeds, not the probability of an exploit on a real platform.

## Safeguards evaluated

- **Time-weighted cap:** integrate observable cap over the common pre-close window and require 300 seconds of age. Funding earlier remains allowed; the attacker is retrained.
- **Daily routing budget:** at most 25% of winner backing at close may be spent through recommendations per day. This is a whole-order limit; blocked orders fall back to the preferred mint without a failed-transaction cost. It is a flow limit, not an escrow fund. An attacker can increase the reference backing by purchasing before close.
- **Six-hour expiry:** after expiry, new orders return to ordinary direct choice. There is no forced sale or automatic re-election.
- **Relative-price limit:** offer the direct asset if the winner's marginal price exceeds 1.5 times the preferred asset's. Integer comparisons enforce this decision. It is meaningful only for this study's identical curve calibration, not arbitrary differently denominated real tokens.
- **Combined:** apply all four, including under 90 extra spam launches. Reducing attack returns by nearly disabling routing must not be confused with preserving the full economic benefit.

Extra 45-basis-point router fees apply only to routed purchases in their sensitivity and are paid from the same all-in budget. This is a generic execution-cost stress, not a replica of Pump's complete interface fee policy.

## Product implication

The concrete product is a shared narrative feed and an optional execution router over independent markets. A creator can launch without joining a fee pot. A coin page can offer the current lead while preserving direct purchase. Every purchase names the received mint and quote limits; a label change never changes old rights. External interfaces remain able to trade the original mint.

Pump's official documentation currently describes no platform creation fee, with network transaction costs and required account deposits still payable, and curve trading without a creator liquidity seed. That supports the launch-access analogy, not an assertion that Pump already implements this narrative mechanism. [Official fee page](https://pump.fun/docs/fees), [official program description](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md).

See `PERMISSIONLESS_C_PRODUCT_DESIGN.md` for entry flows, rights, late launches, costs, and incentives. The in-conversation concept contains illustrative coins and sends no orders.

## Evidence and reproduction

`c_permissionless_study/` contains the predeclared plan, frozen policies/source hashes, training/pilot/confirmation manifests, raw compressed runs, paired effects, summaries, attack and same-policy controls, representative traces, exact-hash replays, new test output, and repository preservation check. The bundle records 5600 completed confirmation worlds with no run exception.

To reproduce without overwriting this bundle, copy the supplied `source/c_followup` directory into `work/c_followup` under a new empty working directory. Use Python with numpy and pandas. Run the following in sequence, keeping the existing research folder read-only:

```text
python -B -m unittest discover -s work/c_followup -p test_open_model.py -v
python -B work/c_followup/run_study.py init
python -B work/c_followup/run_study.py pilot
python -B work/c_followup/run_study.py train
python -B work/c_followup/run_study.py confirm
python -B work/c_followup/run_study.py analyze
```

On another machine adjust only the repository path used for its read-only preservation inventory before initializing the new study; the new plan will capture that source change. Do not overwrite or pool the existing confirmation bundle. The saved original repository and the isolated upstream source copy remain byte-identical to their captured hashes.

## Limits on the decision

This study can falsify a particular synthetic routing design and quantify behavior within its assumed model. It cannot establish user willingness, honest creator entry, a production identity/grouping system, an equilibrium spam rate, bot competition, optimal ordering protection, Pump-equivalent markets, or production permissionlessness. A go decision for real deployment would require those additional kinds of evidence. A better discovery interface is a testable product hypothesis even if electing a permanent financial winner is not supported.
