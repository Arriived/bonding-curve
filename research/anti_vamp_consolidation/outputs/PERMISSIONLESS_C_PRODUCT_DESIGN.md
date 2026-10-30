# Open-launch narrative consolidation: product and mechanism

30 October 2026. Concept design accompanying a synthetic follow-up study. This is not a deployment specification or an audited on-chain implementation.

## The product in one sentence

Anyone can launch an independent coin; related coins share a discovery page, and a buyer can explicitly choose the group's current lead when placing a fresh order.

The grouping joins attention. Only an authorized purchase moves money into another mint. Existing holders, collateral, and creator fees do not move because a label or ranking changes.

## What “free to launch” means

Pump's official fee page, last updated 17 October 2026, says creating a coin has no platform fee; the creator still pays the Solana network transaction fee and required account deposit. Its program documentation describes immediate curve trading without creator-provided liquidity. These are separate ideas: zero platform launch fee, who pays network/account costs, and no mandatory liquidity seed. [Official fees](https://pump.fun/docs/fees), [program description](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md).

Our proposed default follows those three distinctions. A creator can start without buying their own token. The first actual buyer funds issuance. Each mint has independent backing; ten launches do not receive ten subsidized reserves. Optional network sponsorship has an identified payer, finite budget, and measured costs. All costs in the simulation are abstract synthetic amounts, not conversions from current SOL prices.

## Two useful entry points

**Narrative first.** A person opens a single “Moon dog” page instead of ten repetitive feed cards. The page lists each independent coin and its actual mint, plus a temporary lead recommendation. “Buy the lead” names the received mint before confirmation. “Choose a coin” leads to its ordinary direct market. The recommendation has a published rule, timestamp, and expiry; it is not a claim of authenticity or future returns.

**Coin first.** A person opens ORBITDOG's page. Its direct purchase remains available. A separate offer says “This coin belongs to the Moon dog group. Review the current lead instead.” Only taking that offer changes the received asset. A copied ticker, URL visit, or existing token balance never grants routing permission.

The accompanying interactive concept uses fictional coins and illustrates both entry points. It sends no orders.

## Layers and authority

| Layer | Proposed behavior | What it does not confer |
| --- | --- | --- |
| Launch program | Anyone may create an ordinary funded-issuance market, subject to network execution and costs | Creation of other holders' money or a free redeemable allocation |
| Narrative index | Group related entries on one page; show disputed and late entries; permit alternative indexes | Ownership rights over any coin, power to seize backing, or proof that two creators are the same person |
| Public ranking | Compute a temporary lead from published observations and a frozen cohort | A guarantee of genuine demand, Sybil resistance, or a permanent canonical coin |
| Optional router | Honor an order binding the actual received mint, budget, fees, output limit, expiry, and fallback | Control over purchases on unrelated interfaces or external venues |
| Ordinary direct market | Continue buying and selling the selected mint independently | A mandatory contribution to the lead or surrender of losing holders' rights |

Permissionless creation can coexist with a curated interface. A production design must state which parts can be used without its operator. Alternative interfaces can use different narrative indexes and recommendations. The simulation is a model of open entry and optional routing, not a proof that an implemented chain service is permissionless.

## Open entry and cheap spam

A token may be created after the contest closes and still trade immediately. It can appear in the group with “late entrant” status, but cannot rewrite an already signed order or reopen the finalized cohort. A later contest would need a new public cohort/rule version and new user consent; the present study has one election only.

Do not hand each new mint an extra guaranteed slot in the main attention feed. One narrative card can represent many mints. Within it, users can inspect all entries. Grouping errors and ranking manipulation still require explicit handling; displaying one group does not establish that a classifier or score is correct.

No launch-count, per-wallet-holder, or per-wallet contribution bonus is presumed Sybil-safe. An attacker can create many mints or wallets. Any costly restriction must charge the actual actor-funded resource or identify a funded sponsor; it cannot assume known human identities.

## What could make creators join?

Ordinary coin creators retain their mint and its normal creator fee. Group discovery and optional referrals may be useful, but the study has not measured that value or creator willingness to participate. Redirecting traffic can also reduce a losing creator's expected income. They may launch through another venue, reject the interface, or encourage followers to use direct purchases.

Possible referral compensation would have to come from disclosed execution revenue or a named acquisition budget. Do not manufacture a reward per copy launched or promise losing creators a share of nonexistent winner revenue. The tested creator-outside setting is an exogenous stress, not a solved entry equilibrium.

## Safeguards under test, not assumed solutions

1. Time-weight the observed cap across the common contest window and require minimum age. An attacker can respond by funding earlier, so this needs retrained attacks.
2. Limit recommended purchase flow per day relative to the lead's actual backing at close. This limits a predictable buy wall, but can reduce useful routing and favor early orders. An attacker can also increase the reference backing. The simulation tests these responses.
3. Expire the recommendation after six hours, then return to ordinary direct choice. This is an expiry, not a forced sale or a silent new election.
4. Offer the direct coin when the lead exceeds a declared relative-price limit. This comparative rule is meaningful only within the simulation's identical curve calibration; real assets need actual asset-specific quotes and signed output limits.

Combining safeguards can suppress both gains and attacks. A positive result must distinguish that tradeoff from merely disabling the mechanism.

## Boundaries of the follow-up

The experiment uses the prior independent linear curve's integer ledger, 64 funded traders, fixed total endowments, and a fixed seven-day opportunity tape. It tests no mandatory seed, free creation, 0/10/90 extra spam mints, late launches, outside creators, reach/consent, a raw token-feed stress, grouped incoming intentions, fee costs, and a bounded attack search. It does not reproduce Pump's virtual-reserve formula, graduation/AMM migration, real content moderation, historical demand, user attention growth, creator entry equilibrium, or unrestricted attacker programs.

The proposed interface is therefore best understood as a discovery and execution layer over independent markets. Whether it creates a better market remains the empirical and adversarial question.
