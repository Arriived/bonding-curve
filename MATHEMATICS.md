# Mathematical foundation

All statements in this file concern the supplied quadratic model, not a live
launchpad or historical memecoin market. Token quantities must use a fixed,
comparable denomination; changing a token's unit size changes this model unless
coefficients are transformed accordingly.

Let `q_i >= 0`, `Q = sum(q_i)`, `p0 > 0`, `k >= 0`, `0 <= lambda <= 1`.

```
R(q) = p0 Q + k/2 [(1-lambda) sum(q_i^2) + lambda Q^2]
p_i  = dR/dq_i = p0 + k [q_i + lambda sum_{j != i} q_j]
H_ii = k; H_ij = k lambda (i != j)
```

The Hessian eigenvalues are `k(1-lambda)` (multiplicity n-1) and
`k[1+lambda(n-1)]` (multiplicity 1). The surface is convex. At lambda=1,
prices depend only on total supply: independently named tokens lose independent
marginal price discovery. If k=0 all prices are constant.

## Exact execution and solvency

For a purchase of `d` units, with the pre-trade marginal price `p_i`:

```
buy gross  = R(q+d e_i)-R(q) = p_i d + k d^2/2
sell gross = R(q)-R(q-d e_i) = p_i d - k d^2/2
buy cash out = (1+f) buy gross
sell cash in = (1-f) sell gross
```

Fees are a proportion `f` of the gross reserve difference. They are credited to a
separate treasury. They are not backing. A reserve donation is a separately
identified buffer and does not alter prices or become redeemable token backing.
Starting reserves below R are rejected. A zero reserve-capital setting means
explicit automatic funding of exactly R, never an unbacked genesis allocation.

By induction on valid buys and sells, `actual reserve = R(q)+donated buffer`.
Gross cashflows telescope along any path. A full redemption pays exactly initial
R gross, independently of order, and leaves the buffer. Fees lower holders' net
receipts. A token creation with zero supply changes neither Q nor R. No isolated
closed trade loop generates gross profit without another participant's trade.
These are accounting proofs, conditional on the stated model and valid balances.

Two accounts buying the same final supply in different orders pay the same
aggregate gross amount, but can bear very different individual costs. Solvency
does not prove fairness, absence of manipulation, or useful price discovery.

## Liquidity, price impact and capital

The own-token absolute price slope is **k for every coupling**. Buying Token A
changes Token B by `k lambda d_A`. For a fixed state vector, coupling increases
the price intercept and the exact cost of any positive purchase whenever other
tokens have positive supply. It does not flatten the own-token curve. A fixed
cash budget can show lower *relative* slippage because it buys fewer units at a
higher starting price. That is not proof of more depth for a fixed quantity.

An equal-supply comparison starts with different funded capital. An equal-capital
comparison must change supplies. For equal per-token starting supply q:

```
R = n p0 q + k/2 n [1+lambda(n-1)] q^2
```

The positive root is calculated using a numerically stable quadratic inverse.
The comparison workflow matches required backing; any explicit donation is
additional. Exogenous random shocks match across models. Cash constraints,
momentum responses and filled quantities may diverge endogenously.

For a purchase budget B inclusive of fees, set `b=B/(1+f)` and:

```
d = 2b / [p_i + sqrt(p_i^2 + 2 k b)]
```

## Market cap and liquidation

```
M = sum_i p_i q_i = p0 Q + k [(1-lambda) sum q_i^2 + lambda Q^2]
M = 2 R - p0 Q
```

With positive supplies and p0, collective quoted cap is between R and 2R.
Collective gross liquidation is exactly R, not M, assuming all holders redeem and
the reserve is fully funded. Collective net liquidation with constant fee f is
`(1-f)R`. An unowned donated buffer is excluded.

Token i's full first-exit gross quote is `p_i q_i - k q_i^2/2`.
The sum of token first-exit quotes exceeds collective executable R by
`k lambda sum_{i<j} q_i q_j`. They are mutually incompatible first-exit states.

A wallet holding vector h can redeem all its holdings first for exactly:

```
L(h | q) = p(q) dot h - k/2 [(1-lambda) sum h_i^2 + lambda (sum h_i)^2]
```

This is path-independent for that wallet's aggregate gross exit, while other
holders' holdings remain fixed. Different wallets' first-exit quotes cannot be
summed into collective proceeds either. Marked P&L and hypothetical first-exit
P&L are distinguished from realized cash P&L. Average cost is the reporting basis.

## Attribution, contagion and transfers

From a starting state to a later state:

```
Delta p_i = k Delta q_i + k lambda sum_{j != i} Delta q_j
```

This decomposes price change exactly into own issuance and cross-token issuance.
It is an arithmetic attribution, not a causal model of real-world investor demand.
A full sale of d units of A reduces every other token's price by `k lambda d`.
Independent curves have no such mechanical contagion. Remaining holders can lose
paper value even as every redemption is paid and the reserve remains solvent.

The initial reserve contains cross terms `k lambda sum_{i<j} q_i q_j`.
Who pays and who later receives these terms depends on entry and exit order.
Calling this a subsidy is meaningful only with the holder groups and transaction
sequence specified. There is no automatic net value creation from reserve pooling.

## Cross-token pending-order attack

Let the attacker buy b units of B, a victim then buy a units of A, and the attacker
sell all b. With fixed quantities, no fees and no other intervening trades:

```
attacker gross profit = k lambda a b
victim extra gross cost = k lambda a b
```

The attacker's pre-victim buy cost is `C = p_B b+k b^2/2`.
With constant proportional fee f on both attacker trades and network expense g:

```
net profit = (1-f) k lambda a b - 2 f C - g
```

This applies only if the attacker can fund `(1+f) C`, the victim fills, and the
assumed ordering occurs. The victim's increased inclusive payment is
`(1+f) k lambda a b`. A tight payment cap can reject the victim, leaving an
attacker round trip with fee and network losses. Competitors change costs and
redistribute proceeds according to their order; competition is not assumed to
eliminate attacks. No private ordering access or real gas process is simulated.
The exact workbench also reserves both network charges in the attacker's capital
budget and transfers those charges to an explicit network account. The market
Monte Carlo scenario assumes zero network charges; it does include trading fees.

There is no fee-free isolated curve-draining arbitrage: the reserve potential
telescopes on a closed path. The attack transfers victim value; it does not
violate backing. At lambda=0 this *cross-token* attack yields zero gross profit;
that says nothing about same-token sandwich attacks in other mechanisms.

## Scaling and price multiples

At fixed positive per-token supply, coupling creates an O(n^2) reserve term and
O(n) price intercepts. A new token with zero supply begins at
`p0+k lambda Q`, even with no demand of its own. Quote and trade arithmetic can
still be O(1) using cached Q and sum of squares. Full reporting and wallet storage
are O(n) and O(n * wallets) respectively; computational and economic scaling are
different questions.

To multiply a current marginal target price p by m via its own issuance requires:

```
d = (m-1) p/k
external gross capital = p d + k d^2/2 = p^2 (m^2-1)/(2k)
```

Increasing its intercept makes the same *relative* run more expensive at fixed k.
Unrelated issuance can raise its paper price without purchases of that token,
but someone must pay the other curve's exact issuance cost. The `growth` table
also evaluates that route, which is unavailable at lambda=0. This is a linear
marginal price curve, not an exponential curve, and the cap identity limits paper
cap relative to current backing. It does not predict external secondary markets.

## Parameter integrity and numerical scope

Parameters are immutable per reference run. For a hypothetical coupling change:

```
Delta R = k Delta lambda sum_{i<j} q_i q_j
```

Increasing coupling on an occupied system needs explicit new collateral;
decreasing it requires an explicit collateral-ownership policy. The dashboard
creates a new run on parameter changes and never silently reprices a live ledger.

The Decimal engine uses 160 significant digits and bounded external inputs
(<=1e18, <=18 fractional places, <=100,000 tokens), with no quantization of cash
flows. Cost-basis divisions can be rounded but do not affect reserve or cash
conservation. This is not six-decimal USDC settlement; on-chain rounding and dust
policies remain untested. Float64 simulations are regression-tested against the
reference on matched randomized trades. Their raw discrepancy and material
shortfall after an explicit relative tolerance are reported separately.
