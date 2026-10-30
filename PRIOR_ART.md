# Narrative consolidation: prior art and evidence boundary

Phase 1, 30 October 2026. This is an off-chain research specification. No new
economic simulation, deployment or historical calibration has been completed.
Protocol documentation describes mechanisms; it does not establish their
economic success. Sources below were consulted on this date. Mutable documentation
and indexed pages are not pinned deployed-code audits.

## 1. Existing research in this repository

| Material inspected | Finding relevant to the new study | Reuse boundary |
| --- | --- | --- |
| `bonding_lab/engine.py`, `fast.py`, `MATHEMATICS.md`, `RESEARCH_FINDINGS.md`, `PHASE1_AUDIT.md` | Exact funded reference accounting; independent control at coupling zero; positive quadratic coupling leaves own absolute slope unchanged and permits cross-token ordering transfers. | Reuse accounting concepts and independent execution only. No new positive cross-price terms. |
| `bonding_lab/phase2/`, `PHASE2_DESIGN.md`, `PHASE2_FINDINGS.md` | Shared AMM depth involves paid inventories and LP risk; equal capital alone does not align price, inventory or risk. | Reuse finite-dealer, capital-matching and depth diagnostics after separate validation. Do not import its differently numbered four architectures. |
| `bonding_lab/copycat/`, `research/copycat_diversion/DESIGN.md`, `FINDINGS.md`, `WINNER_REANALYSIS.md` | Already studies independent curves, buyer-owned principal splits, alternative fee/treasury/holder interpretations, grouping, leader rules and funded attacks. | Reuse reference patterns, actor-level budgets, held-out policy search and provenance. Fixed diversion and synthetic badge steering do not establish consent to a different token. |
| `bonding_lab/agents.py`, `experiments.py`, `simulation.py`, `dashboard.py`, `tests/` | Seeded intentions, distributions, exports, replay and accounting/property/application tests exist. | Adapt through new modules. Existing behavior is synthetic and its event horizons do not establish 24-hour or seven-day survival. |

The copycat reanalysis explicitly changes the objective from original-token
survival to concentration on whichever token wins. That clarification is retained:
a copy winning is not inherently an attack. A financially captured winner that
repels subsequent voluntary demand can still be an economic failure. Historical
reported test counts are not the current baseline; see `RESEARCH_PLAN.md` and the
new Phase 1 evidence directory.

## 2. Independent launches: Pump

**Implementation documentation available.** Pump's official repository describes
per-mint bonding curves using virtual reserves alongside real reserves, followed
by migration into PumpSwap. Its newer documentation also describes multihop
routing. These operations do not select one narrative winner or authorize
replacement of a buyer's chosen mint. Our initial linear independent curve is a
controlled research instrument, not a replica of Pump's reserve formula.
[Pump program](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md),
[official repository and updates](https://github.com/pump-fun/pump-public-docs).

An important accounting detail is version-dependent fee custody: newer trade
instructions can retain accrued protocol/creator fees in curve or pool custody
until swept. Physical vault balance therefore need not equal backing available
to traders. We separate fee liabilities from market reserves even when custody
is shared. We do not hard-code rates from old examples or third-party summaries.
[Fee sweep specification](https://github.com/pump-fun/pump-public-docs/blob/main/docs/instructions/SWEEP_FEES.md).

## 3. Prism: close comparison, with limited verification

**Published product specification; execution unverified here.** Prism's indexed
first-party page describes narrative grouping, a composite score, a committed
hidden close in a 28–32 minute range, and pooled creator fees split 60% to winner
buy-and-burn, 30% to its creator and 10% to the platform. Losing coins continue
trading. It also describes custodial baskets buying several ranked candidates.
[Prism mechanism page](https://prismlaunch.fun/how-it-works).

Direct fetches of that page failed; the search index exposed its text. No code
audit, fee transactions, operator behavior or reliable market history was verified.
Its anti-wash and probability language is a claim to test, not validation. A hash
binds a chosen close but alone proves neither unbiased sampling nor secrecy from
its operator. Ranking weights are not calibrated winning probabilities.

The comparison is therefore specific: B studies fee support; C studies authorized
post-election purchase principal; D studies conditional escrow funding one winner.
Prism's baskets already involve purchase principal, so broad novelty for principal
routing is not established. Our difference is elected-winner settlement and
explicit ownership/refund rules, subject to further prior-art review.

## 4. Auctions and launch settlement

**Public implementation.** Gnosis EasyAuction accepts collateralized limit orders
against a supplied token lot, computes a common clearing price, and provides
claims for tokens and unspent bid funds. Cancellation deadlines and funding
conditions are explicit. It supplies useful settlement precedents, not a
multi-candidate narrative election or proof of truthful bidding.
[EasyAuction source and mechanism](https://github.com/Gnosis-Auction/auction-contracts/blob/main/README.md).

**Public implementation and documentation.** Uniswap Continuous Clearing Auction
spreads token issuance through time, with budget/maximum-price bids. Its technical
specification includes graduation, failed-auction refunds, token claims and a
downstream liquidity handoff. Such issuance differs from both a one-shot auction
and our initial D batch subscription; we must compare timing and market-formation
effects separately from narrative selection.
[CCA concepts](https://developers.uniswap.org/docs/liquidity/liquidity-launchpad/concepts/cca),
[CCA technical source](https://github.com/Uniswap/continuous-clearing-auction/blob/main/docs/TechnicalDocumentation.md).

## 5. Shared infrastructure and intent routing

**Public implementation documentation.** Balancer separates Vault token accounting
from pool pricing logic. Shared custody or a shared router does not entitle every
candidate to the same cash. Our accounting keeps market ownership and liabilities
separate; a genuinely shared inventory pool would require a distinct risk-bearing
LP model, beyond the primary A–D comparison.
[Balancer Vault](https://docs.balancer.fi/concepts/vault/).

Balancer's weight-shifting liquidity bootstrapping pools provide another launch
control: scheduled weights affect sale pricing and some configurations restrict
project-token sales. Those restrictions change exit rights and must not be
credited to winner selection in a matched comparison.
[LBP documentation](https://docs.balancer.fi/concepts/explore-available-balancer-pools/liquidity-bootstrapping-pool/liquidity-bootstrapping-pool.html).

**Public protocol documentation.** CoW aggregates intents and compares solver
settlements; consistent directed clearing prices can reduce ordering dependence
within a batch. Signed order fields identify the sold and bought assets and an
expiry. We borrow the principle that changing the received mint requires new
authorization or an existing conditional authorization. Batching alone does not
prevent pre-batch inventory accumulation or capture of the election.
[CoW auctions](https://docs.cow.fi/cow-protocol/concepts/introduction/fair-combinatorial-auction),
[signed order fields](https://docs.cow.fi/cow-protocol/reference/core/signing-schemes).

## 6. Migrations, identity and market manipulation

**Public token migration implementation.** Polygon's Ethereum MATIC/POL migration
uses an explicitly defined conversion and user approval. That is a token upgrade
with specified rights, not permission to seize one speculative asset's reserve
and buy an unrelated winner. Pump's curve-to-AMM migration likewise changes the
venue without choosing another narrative mint. Our loser conversion must use
actual redemption proceeds and a separate authorized winner purchase.
[Polygon migration instructions](https://support.polygon.technology/support/solutions/articles/82000912953-how-can-i-migrate-to-pol-),
[migration source](https://github.com/0xPolygon/pol-token).

**Research evidence.** Douceur's Sybil analysis explains why addresses do not imply
independent identities. Capital-linear scoring avoids an automatic gain merely
from splitting the same capital, but remains plutocratic. Per-wallet bonuses,
concave weights and concentration penalties can restore splitting incentives;
actor ownership is simulation ground truth, not a production identity oracle.
[The Sybil Attack, 2002](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/).

**Research evidence.** Flash Boys 2.0 documents transaction-order extraction in
DEX markets. A visible migration or scheduled fee buy creates a same-token
ordering opportunity even with independent candidate prices. A winner-take-all
reward can also make capital temporarily committed to capture the title rational.
These are hypotheses for funded attack optimization, not estimates of attack
frequency on the proposed platform.
[Flash Boys 2.0](https://arxiv.org/abs/1904.05234).

## 7. Historical data access and calibration status

Provider documentation exposes pair search/current metrics through DEX Screener
and transaction history through Solana RPC. Neither a keyword hit nor a pool's
creation time identifies the complete launch cohort. Rolling volume and buy/sell
counts cannot reconstruct quote net flow, beneficial ownership or decayed launches.
[DEX Screener API](https://docs.dexscreener.com/api/reference),
[Solana history/indexing limitations](https://solana.com/docs/payments/accept-payments/indexing),
[transaction response schema](https://solana.com/docs/rpc/json-structures).

Phase 1 attempts public keyword access for `PNUT` and `NEIRO` solely as discovery
probes. They are search terms, not verified historical clusters. Request status,
raw successful responses and limitations are recorded by
`research/narrative_consolidation/phase1/probe_public_data.py`. A browser-tool
request to the PNUT API URL was inaccessible; direct HTTP results are recorded
separately. No paid dataset, wallet signature, private API credential or real-fund
transaction is used. A successful snapshot is not historical calibration.

**Observed access result:** both initial sandboxed probes failed DNS resolution;
those results remain in `data_access_probe_sandbox.json`. An authorized network
retry succeeded with HTTP 200 for both terms, each returning 30 pair records and
17 distinct `(chain, base-token address)` keys. Raw JSON and hashes are preserved.
These are current keyword snapshots with overlapping venues and unverified
membership, not counts of launches competing in a historical event. No historical
cluster was verified and no behavioral parameter was calibrated. Later economic
experiments must remain explicitly synthetic unless a fuller collection succeeds.

Before any historical claim, enumerate mints and creation transactions, label
same-event candidates independently of later success, preserve failed/delisted
tokens, reconstruct curve and post-graduation flows without double-counting venue
transfers, and publish coverage gaps. Common-funding links may suggest coordinated
wallets; they neither prove shared control nor count humans. No empirical routing
acceptance, loyalty, retention or creator-participation estimate is available here.

## 8. What remains distinctive and what remains unproven

The testable combination is narrative membership plus a contest, economically
authorized winner principal, conditional settlement, and matched behavioral
counterfactuals. Every component has precedents. This review establishes neither
patent novelty nor a defensible business moat.

Fee recycling, a larger winner reserve, concentrated flow, a higher displayed cap
and longer organic survival are different claims. The research succeeds only if
the latter outcomes survive abandonment, strategic selling, creator refusal and
equal-capital comparisons. Existing documentation does not answer that question.
