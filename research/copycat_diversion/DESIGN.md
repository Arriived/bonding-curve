# Copycat diversion: design before implementation

Off-chain synthetic research, 29 October 2026. Reuse `bonding_lab.engine.Curve`
and its validated `FastBook` at coupling=0. This is routing/taxation between
independent curves, not a shared bonding surface or empirical market study.

## Rules and accounting

Each token has a unique ID, creator, launch time and displayed ticker. All use
the same canonical quantity unit and fixed p0/k/fee. Nobody gets free supply.
Creators, snipers, bundlers and attackers must pay for curve-issued inventory.

A copy buyer submits budget B (excluding declared network expense). If an active
leader exists in that token's matching group and the target is not that leader,
D=alpha B, for alpha in 1%,3%,5%,10%. The copy curve receives an inclusive-fee
budget `(1-alpha)B`; otherwise the full B. No sell diversion applies. The usual
curve fee f applies to exact reserve differences. Cash-transfer diversions have
no invented extra curve fee. Leader purchases have the same existing fee.

- **Creator:** D is transferred to the leader's creator, not its reserve.
- **Holders:** D is distributed pro rata to eligible leader holdings immediately
  before the copy purchase. Protocol/dead balances are excluded. If nobody is
  eligible, diversion is waived; there is no first-holder escrow jackpot.
- **Buy leader:** D buys the leader on its independent curve. **The copycat buyer
  owns the leader tokens**, as specified by the user. A non-distributing treasury
  is a sensitivity. Payout to existing holders is already the preceding variant.
- **Buy/burn:** primary interpretation is an inaccessible burn-address balance:
  redemption rights are surrendered, while the funded issued-not-redeemed pricing
  counter remains. This is explicitly called **buy-and-lock** in the findings.
  A treasury that never sells is close to this case, apart from redemption/overhang
  rights; locked units and treasury units are separated in the metrics.
- **Literal supply-burn sensitivity:** purchase, then destroy the acquired units
  and reduce the curve's outstanding pricing supply without paying redemption.
  Required collateral falls; the retained cash becomes an explicit surplus.
  This restores the pre-purchase marginal price. It is economically different
  from a dead-address balance and is never silently treated as price support.

For p=p0+kq, exact gross buy/sell execution is `p d +/- k d²/2`. A buy budget C
inclusive of fees mints the positive quadratic inverse of `C/(1+f)`. The Decimal
reference rounds quantity down to 1e-12; any unspent cash stays with its payer.
Financial transfers use at most 18 decimal places and deterministic residual
allocation. The float implementation is validated against this reference.

Every route prevalidates funding/limits before mutation. Cash, token ownership,
fee treasury, donated burn surplus and locked inventory are audited separately.
Leader identity is snapshotted atomically per routed transaction. Protocol
treasury and burn balances cannot trade as simulated users. All P&L uses actual
cash after funded exits, with closing-order sensitivities, not quoted market cap.

## Leader selection

1. **First launched:** oldest token in the matching group, deterministic ID tie.
2. **Threshold:** first to reach quoted `p*q` of $100k or $1M. No qualified token
   means no diversion. Fixed selection latches the first crossing; flip mode uses
   the largest currently qualifying cap. A fixed leader need not retain the cap.
3. **Held market-cap lead:** largest quoted cap continuously for 5,30,120 minutes,
   with minimum token age 5 minutes. A champion's dwell clock resets when another
   eligible token overtakes it. This primary rule means continuous leadership,
   not an instantaneous cap or a loosely sampled moving average.
4. **Distinct-wallet volume:** highest sum of the first gross buy by each funding
   address in the last 5,30,120 minutes, minimum 3 distinct addresses and age 5.
   Repeated turnover from one address does not help. Sybil addresses count as
   addresses, not people; this is deliberately stronger than raw wash volume.
   Raw all-trade volume is available as a weaker sensitivity.

Fixed mode latches the first eligible leader. Flipping mode updates at transaction
boundaries, either without cooldown or after a 30-minute cooldown. A cooldown
delays switches; it does not certify identity. First-launched selection cannot
meaningfully flip, so duplicate settings are omitted. Undefined-leader time is
reported instead of discarding it from original-identification statistics.

## Matching and the semantic denominator

Exact matching preserves case and spaces. Case-insensitive matching folds case
only. Fuzzy matching uses NFKC, case folding, 0->O, digit/space removal and edit
distance <=1 to an existing stable group anchor; ties choose the oldest anchor.
Groups do not retroactively merge. Fuzzy admission is therefore explicit and
order-sensitive, not a claim to solve human ticker identity.

All original, copied and evasive ticker spellings belong to the same *semantic
campaign* for outcome measurement, including those that evade the matching rule.
The denominator never silently drops ELON1/ELONN/EL0N/spaced/homoglyph copies.
Candidate evasion strings include spellings beyond the fuzzy edit radius.

## Controlled market and controls

The original launches at time 0; fourteen baseline copies arrive over time.
Some use exact tickers and others near tickers. New buyers have funded wallets,
configurable confusion and informed fractions. Informed buyers consult the
selected leader; organic wrong-copy choices use matched random impressions.
Snipers, funded coordinated buyers, ordinary copy creators and a vamper act on
declared schedules. Each organic arrival has its own wallet and a scheduled or
terminal exit, so early/late and leader/copy outcomes are attributable.

Controls retain the same independent curves and leader-information policy, with
zero diversion. A display-only badge steers 25%,50%,75% of organic impressions
toward the displayed leader, without financial entitlements. Each financial
variant also has a matched zero-diversion control using the same election/matcher.
The badge is an assumed behavioral intervention, not measured consumer behavior.

Matched seeds fix buyer arrivals, budgets, confusion draws and exit intentions.
Fills and leadership may diverge endogenously. All candidate strategies have the
same attacker endowment. Launch fees and network expenses are paid to explicit
accounts; aliases receive funded transfers, not new capital. The attacker cannot
pre-launch before the original in the primary experiment. Pre-squatting would
require a separate prior-information assumption.

## Exact implications to test

Let rho=(1-f)/(1+f). With no intervening trades:

- Creator/holder cash diversion leaves a copy buyer's copy-only round-trip cash
  at `rho(1-alpha)B`, versus `rho B` without diversion. Cash recipients gain D.
  These payouts add no mechanical curve depth and need not consolidate backing.
- Buyer-owned leader purchases leave the buyer with two funded positions. Their
  combined immediate redemption is `rho B`, before network expense. This is a
  forced portfolio split, not a free liquidity gain or an additional cash tax.
- Own-copy washing by the leader's creator gives actor net cash change
  `-(1-rho)(1-alpha)B`: self-paid diversion is not external revenue. Launch costs
  and network costs make the loop more expensive.
- If a copy-spam actor captures fraction phi of real outsiders' diverted copy
  spending V, direct-payout break-even is
  `phi alpha V + other_realized_profit > launch_cost + election_cost + wash_loss`.
  For constant phi and known other terms, solve for V. Exclude self-funded wash
  turnover from V. Holder phi varies; use actual snapshot-weighted payments.
- Cap threshold M needs `q*=(-p0+sqrt(p0²+4kM))/(2k)` and
  `R*=(M+p0 q*)/2`. Capital is about M/2, but a reversible no-external-trade pump
  costs only `2 f R*` in fees, plus launch/gas. A fixed title can outlive that pump.
- A holder-dividend front-run of b units before payout D earns
  `D b/(q+b) - 2f(p b+k b²/2)` before network cost when the attacker starts with
  no leader inventory. Share capture and acquisition cost must both be charged.
- A front-run before a fixed diverted buy budget D mints victim quantity
  `d(b)` at leader price p+kb. Attacker gross profit is `k b d(b)`, not the
  fixed-quantity formula with an assumed unchanged victim fill. Net profit is
  `(1-f)k b d(b)-2f C_attacker`, subject to funded capital and leader-leg minimum
  output. Buy-and-lock and never-selling treasury have the same immediate effect.
- Literal supply-burn cancels this price increment. A simple before/after leader
  round trip has zero gross trading profit; actual remaining risks include leader
  selection and attention capture. Pure creator transfers do not reward buying
  leader inventory merely before the payout.
- Exact-string matching can be evaded by a case or spacing change. Fuzzy matching
  can still be evaded by out-of-radius spellings if human confusion persists.
  This is conditional on the declared human-confusion assumption, not proof that
  every spelling is equally successful in a real market.

## Attack search and evidence standard

Each family includes abstention. Search funded policies over launch time, pump
size, residual holdings, exit time, alias count, wash frequency, spam count and
ticker spelling as appropriate. Capital race targets actual eligibility; spam
captures confused impressions; evasion searches actual matcher boundaries;
flipping times observable windows/cooldowns; front-running sizes against the
actual payout rule, fees and minimum output. No future random tape is exposed to
an executing policy. Training seeds choose policies; different seeds evaluate them.

Report **best found in the disclosed search space**, not a global best response
or proof of security. Compare the chosen attack with the same strategy under
zero diversion and with the control's independently selected best response.
Use broad parameter screening followed by a separate, larger held-out confirmation
of finalists. Do not pool different horizons, seed roles or selected policies.

Consolidation uses executable independent-curve redemption, accessible circulating
claims, raw reserve, locked/burn surplus and organic versus attack-generated volume
separately. Also report actual original share, largest-token share, leader tenure,
misidentification, confused-buyer cash P&L, recipient gains, vamper P&L and early/
late leader/copy cohorts. A rising cap, a dead-address position or a surplus with
no holder claim is not automatically genuine accessible liquidity consolidation.
