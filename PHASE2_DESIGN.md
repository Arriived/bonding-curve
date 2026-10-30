# Phase 2 mathematical design and comparison protocol

29 October 2026. This document precedes alternative-engine implementation. All
proposed mechanisms are research models; none is an endorsed launchpad design.

## 1. Audit questions and evidence boundary

For the original surface, `H_ii=k`, `H_ij=k lambda`, convexity, gross path
independence, funded solvency, `M=2R-p0 Q` and the cross-order transfer `k lambda a b`
are algebraic properties. Profit frequency, adoption, run propensity, welfare and
filled-trade average slippage depend on the synthetic policy and starting state.
The old equal-capital comparison equates genesis backing and additional trading
cash, with the same random tape. It does not equate initial prices or inventory
quantities. At a quadratic curve, relative average slippage is `k d/(2p)`; for a
fixed small cash order B it is approximately `k B/(2p^2)`. Higher p alone reduces
that statistic. A lower statistic is not a causal liquidity result.

The audit will verify manifest source hashes against a preserved legacy snapshot,
recompute seed summaries, reproduce selected seeds and run the original tests.
Historical results are retained. A strict genesis funding fix must not silently
rewrite the provenance of the previous research.

## 2. Economic units and admission

Let `S_i` be immutable, verified, full authorized raw supply of token i, and
`x_i=q_i/S_i` its curve-issued fraction, `0<=x_i<=1`. Prices `P_i` below are USDC
per whole authorized-supply claim; raw-token prices are `p_i=P_i/S_i`.
Redenominating raw balances and S by the same factor leaves x, all cashflows,
economic depth and external valuations unchanged. S is an economic issuance cap,
not an oracle price or a creator-selected tuning coefficient. Changing the cap,
rebasing, transfer taxes and mint authority are outside the admitted asset type.

Admission is permissioned into a fixed-capacity cohort (maximum 1,000 assets):
verify the immutable cap/transfer behavior, register S, begin at x=0, and preserve
all existing coefficients. No seed allocation is minted. No coefficients are
renormalized when membership changes. Independent launching is compatible with
screened shared-infrastructure admission; permissionless safety is not claimed.
Sybil asset identities and false cap attestations remain admission risks. The
normalization removes unit dependence, not economic identity dependence.

## 3. Conservative bounded reserve potential

Use USDC coefficients `a_i>0`, `b_i>0`, `gamma>=0`, `tau>0`, and `X=sum x_i`:

```
G(X) = gamma X^2/(tau+X)
R_b(x) = sum_i (a_i x_i + b_i x_i^2/2) + G(X)
G'(X) = gamma [1 - tau^2/(tau+X)^2]
G''(X) = 2 gamma tau^2/(tau+X)^3
P_i = a_i + b_i x_i + G'(X)
p_i = P_i / S_i
```

`0<=G'<gamma` bounds the entire global contribution to each P_i, independently
of token count and others' supplies. The Hessian in x is
`diag(b_i)+G'' 11^T`, positive definite; in raw units its entries are divided by
`S_i S_j`, preserving positive definiteness. Thus prices stay positive and the
potential is strictly convex. Own curvature is `b_i+G''`; cross curvature is
`G''`. Bounded influence is not a claim that coupling improves own depth.

Exact funded execution is `C_i(d)=R_b(x+d e_i)-R_b(x)` for issuance, and
`V_i(d)=R_b(x)-R_b(x-d e_i)` for redemption. Fee f is collected separately.
The reference uses rational arithmetic (Fraction), so this rational potential,
its reserve differences, wallet limits and conservation can be tested exactly.
Float research execution is checked against that reference and declares tolerance.
Gross required reserve is R_b; donated excess is not an LP asset or trader payout.
Full valid redemption telescopes to R_b and leaves zero required backing.

For attacker B purchase b, victim A purchase d, and B exit:

```
t = tau+X
Pi_gross = G(X+b+d)-G(X+b)-G(X+d)+G(X)
         = gamma tau^2 b d (2t+b+d) / [t(t+b)(t+d)(t+b+d)]
0 <= Pi_gross <= 2 gamma tau^2 b d/t^3
Pi_net = (1-f) Pi_gross - 2f C_B(b) - network_cost
```

The victim's extra gross cost equals Pi_gross. Capital, finite issuance capacity,
slippage limits and ordering still apply. The cap limits this transfer; it does
not eliminate it. New assets inherit a bounded starting premium `G'(X)/S_i`.

## 4. Genuine shared-reserve weighted AMM

Implement a separate constant-mean pool with actual USDC c and token inventories
y_i, weights `w0=1/2`, `wi=1/(2n)` fixed at cohort creation:

```
K = c^w0 product_i y_i^wi
P_i = (wi/w0) c/y_i = c/(n y_i)
USDC input B -> token output y_i [1-(c/(c+(1-f)B))^n]
token input d -> USDC output c [1-(y_i/(y_i+(1-f)d))^(1/n)]
```

Full inputs, including input fees, enter the pool. K is nondecreasing with fees;
positive inventories constrain execution. Output is always below the actual
output reserve. Raw-token redenomination changes inventories and invariant scale,
but not economic outputs. LPs own the residual portfolio, not a fixed USDC promise.
Cash positivity is distinct from avoiding marked LP losses or being able to repay
all LPs their original dollar deposits.

At identical total seed value B, stable weight 1/2, common P and token allocation,
compare a hub router with n isolated 50/50 token/USDC pools. Both spend B/2 on
USDC and B/2 buying token inventory. At the aligned start each y_i=B/(2nP).
The shared pool's own-token buy slope is `(1+1/n)P/y_i`; the isolated pool's is
`2P/y_i`. Thus a local depth gain up to about 2x is mathematically possible;
every token does not receive n copies of the common reserve. Finite inventory
and simultaneous all-asset demand are tested separately from one-token quotes.

Toxic-token sales reduce common c and therefore every unaffected token's quote.
With unbounded worthless input, common cash tends toward zero. Finite verified
supply limits but does not eliminate the loss. The loss belongs pro rata to LPs;
there is no insurance token or replenishment assumed. An isolated hub limits the
same sale to that token's allocated cash. We implement that control as a risk
diagnostic, not as a fifth required architecture.

Admission: the AMM is fully seeded using paid token inventory and USDC. Known
bad prices/unverified supply are rejected by a simple declared admission check.
Mid-run weight changes/new assets are rejected; a new asset requires a newly
funded cohort rather than access to old LP cash. A weak-screening counterfactual
admits an asset at an optimistic price before its reference value collapses.
This tests misadmission and post-admission toxicity without claiming screening
can predict future token quality. No live oracle or attestations are integrated.

The weighted invariant and exact-input formula follow the
[Balancer whitepaper](https://docs.balancer.fi/whitepaper.pdf) and
[weighted-math documentation](https://docs-v2.balancer.fi/reference/math/weighted-math.html).
This is an abstract model, not an implementation of Balancer's deployment limits.
A common hub does not itself remove inventory risk: Bancor's own
[account of the 2022 BNT distribution pause](https://support.bancor.network/bancor-amm/bancor-3-mechanics/pause-of-bnt-distribution)
describes price divergence, rebalancing arbitrage and vault deficits. Our experiment
does not reproduce Bancor or infer its safety from this different invariant.

## 5. External markets and arbitrage

Each token has an independent stochastic reference z_i(t), with matched random
innovations across architectures. A finite dealer holds real tokens and cash;
inventory never regenerates. In each event/window, let u_i be net customer buys,
L_i finite depth and s half spread. With `|u_i|<=L_i/2`:

```
external buy cost(d) = z [(1+u/L)d + d^2/(2L)] (1+s)
external sell proceeds(d) = z [(1+u/L)d - d^2/(2L)] (1-s)
```

Executed buys add d to u, sells subtract d. The window refreshes displayed depth
at the next stochastic price; dealer cash and token ownership do not reset.
The dealer can lose money from exogenous quote updates. Its P&L is reported.
These are synthetic finite quote curves, not calibrated external exchange data.

Arbitrage evaluates both routes: mint/buy internally then sell externally; or buy
eligible tokens externally then redeem/sell internally. Both legs must be funded,
inventory-feasible, inside depth/cap constraints, and profitable after fees and a
declared per-route expense. Optimize size numerically over the feasible interval,
execute atomically in simulation and debit expense to a network account. Track
realized bot cash gains, failed opportunities and residual mispricing. Arbitrage
does not automatically identify an LP loss: an issuer sells new claims, whereas an
AMM relinquishes existing inventory. Their liabilities and equity differ.

## 6. Matched budgets and calibration — no free inventory

Every world has the same USDC endowment: sponsor B+E0, external dealer E,
retail T, bot A; the creator and network start with zero cash. E0=.1B is the
dealer's paid seed-token inventory value, and `h_i=E0/(nP)` is identical per asset.

- Curves: sponsor pays B+E0 for genesis issuance; dealer pays sponsor E0 for h_i.
  Sponsor cash left E0, net deployed capital B; required reserve B+E0. Issued
  claims are held by sponsor/dealer and aggregate exactly to outstanding supply.
- AMM: sponsor uses B/2 as cash reserve and pays creator B/2 for pool inventory;
  dealer separately pays creator E0 for h_i. Sponsor cash left E0, net deployed
  capital B; seed inventory costs are fully counted. The creator's remaining
  authorized inventory is finite. Pool NAV starts B.

Thus identical total outside funding does not imply identical USDC backing:
curve external claims themselves fund collateral, whereas AMM token purchases
pay their issuer. Both paths and creator proceeds are exported. Initial marked
genesis gains are never counted as subsequent trading profit. Sponsor P&L is
reported against initial external-marked wealth *and* paid capital, separately.
Curve operator fees are reported as fee income; reserve collateral is offset by
redemption liabilities and must not be called LP profit. AMM LP NAV and loss
versus holding its initial portfolio are reported separately (N/A for curves).

Primary calibration aligns initial marginal P and sponsor net budget B, not just
cash backing. With `a=.2P`, Rseed=B+E0, uniform x:

```
independent / quadratic: x=2 Rseed/[n(P+a)]
independent b=(P-a)/x
quadratic b=(P-a)/[x(1+lambda(n-1))]
bounded: solve Rseed = n x (P+a-G'(nx))/2 + G(nx)
         b=(P-a-G'(nx))/x
```

Set gamma=.2P and tau=1, ensuring b>0. Every calibrated coefficient is exported.
The original quadratic's smaller b under this joint calibration is **a changed
coefficient**, not a refutation of `H_ii=k` at fixed k. Fixed-coefficient,
equal-backing diagnostics are retained to expose the difference. We do not claim
an architecture-independent optimum from one parameter choice.

## 7. Measurements and falsification

Four primary architectures: independent, original quadratic, bounded, weighted
shared AMM. Measure finite exact buy/sell costs for common normalized quantities
and reference-dollar notionals, post-trade price impact, fill rates at a 1% cap,
joint all-token executions, external mispricing and arbitrage extraction, trader
external-marked/realized P&L, fee income, sponsor mark changes, AMM LP NAV/HODL
loss, stable depletion, backing shortfall (curves only), token/cash conservation,
and scale at 2/10/100/1,000 tokens under a fixed total budget.

Run static controls, popularity/independent divergence, one-token crash,
misadmission/toxic inventory, cross-order attacks, and full-redemption tests.
Monte Carlo uses matched shocks, common retail cash, no borrowed tokens/cash,
seed-level paired differences and uncertainty intervals. These intervals describe
this assumed process only. A depth improvement is acceptable evidence only when
capital, starting prices, quantities, inventory depletion and risk borne by LPs
are visible together. The verdict may reject all positively coupled variants.
