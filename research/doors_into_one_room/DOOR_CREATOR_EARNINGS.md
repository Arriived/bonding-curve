# What a door creator actually earns

> **Out of date: regenerate before use.** This document's fee-split numbers
> assume the superseded model: 30% of the fee to the door creator, a 10%
> founder share, 20% to the reserve and 40% to the protocol. The rewritten
> [PERMANENT_CURVE_SPEC.md](PERMANENT_CURVE_SPEC.md) uses **60% to the door
> and 40% to the protocol, with no founder share**. Door fees are now zero, and
> a door costs only its rent. Current verified figures are in
> `outputs/fee_model.md` and `outputs/account_sizes.md`.
> The first-buy multiples in §5 also use the superseded C1 curve. The
> `scripts/door_creator_model.py` outputs must be regenerated against 60/40
> before these numbers are quoted.


31 October 2026. Terminal substitution is switched on, per Ruling 1. Every
number below comes from `outputs/door_creator_model.md`, produced by
`scripts/run_door_creator_model.sh`. On-chain readings are in
`outputs/onchain/pump_fee_config.json`, produced by
`scripts/onchain/run_pump_fee_config.sh`.

Doors parameters are the spec defaults from
[PERMANENT_CURVE_SPEC.md](PERMANENT_CURVE_SPEC.md):

- trade fee 100 bps, of which door creator 0.30% of volume, founder 0.10%,
  reserve 0.20%, protocol 0.40%;
- door fee 0.5 SOL plus 0.009166 SOL rent = **$76 per door** at SOL = $150.

## 1. What share of pump.fun volume goes through terminals

**Not publicly available. Searched, not found:**

- Blockworks Research publishes an "External Trading Platforms" series, the
  amount of bonding-curve volume originating from Telegram bots and other
  trading platforms. It is behind a subscription and could not be read
  ([blockworks.com/analytics/pumpfun/pump-fun-trading-volume](https://blockworks.com/analytics/pumpfun/pump-fun-trading-volume)).
- No public Dune dashboard splitting pump.fun volume by frontend was found.
- Figures in secondary articles conflict, and they describe terminal shares
  of *Solana meme trading overall*, not of pump.fun volume. They are not used.

**So substitution `s` is swept as an assumption, not a measurement:**

- low **30%**;
- mid **60%**;
- high **90%**.

I could not verify a measured figure, and none is presented as one.

Other assumptions are stated where they are used:

| assumption | value |
| --- | --- |
| a creator's own community generates `a` of room volume | 5% or 20% |
| share of flow that picks doors uniformly (ρ) | 5% |
| number of doors in the room (D) | 20 |
| SOL price | $150 |

First-buy trading P&L is reported separately (§5), because anyone can buy the
room token without opening a door.

## 2. Non-founder door creator, over the room's life, net of the $76 door cost

**Door income:**

- With its own traders: `0.30% × (1 − s) × (a·V + ρ·V/D)`.
- With no traders: `0.30% × (1 − s) × ρ·V/D`.

| room volume V | substitution s | door that brings traders, a = 5% | a = 20% | door that brings none |
|---|---|---|---|---|
| $1M | 30% | $34 | $349 | −$71 |
| $1M | 60% | −$13 | $167 | −$73 |
| $1M | 90% | −$61 | −$16 | −$76 |
| $10M | 30% | $1.0k | $4.2k | −$24 |
| $10M | 60% | $554 | $2.4k | −$46 |
| $10M | 90% | $81 | $531 | −$69 |
| $50M | 30% | $5.4k | $21.2k | $186 |
| $50M | 60% | $3.1k | $12.1k | $74 |
| $50M | 90% | $711 | $3.0k | −$39 |

**To recover the $76 door cost**, the creator's own traders must route
**$36.4k** of volume through the door at s = 30%, **$63.6k** at 60%, and
**$254.6k** at 90%.

**The door that brings none** earns nothing from substituted flow. Substituted
flow goes to the *terminal's* door by definition. It earns only from uniform
pickers, which loses money in every room under $50M of lifetime volume, and
even at $50M if substitution is 90%. Its positive cells depend entirely on the
assumed 5% uniform-picking share.

**Where the substituted flow goes:** the terminal's own door. A terminal
routing half of all terminal flow earns per room:

| V | s = 30% | s = 60% | s = 90% |
|---|---|---|---|
| $1M | $450 | $900 | $1.4k |
| $10M | $4.5k | $9.0k | $13.5k |
| $50M | $22.5k | $45.0k | $67.5k |

## 3. The alternative: launching their own coin on pump.fun

**The creator fee is not 0.05% for most coins.** Current values were read
on-chain at slot 463,696,387 from pump.fun's fee program
`pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`. The FeeConfig PDA is
`["fee_config", <program>]`, per the `pump_fees.json` IDL in
pump-fun/pump-public-docs @ `639b87fb45c3adeffa6f7c4a1bf0cb85e392bf22`.

| venue | config account | creator fee |
|---|---|---|
| pump bonding curve (`6EF8rr…F6P`) | `8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt` | **30 bps flat** (protocol 95 bps) |
| PumpSwap canonical pools (`pAMMBay6…EXA`) | `5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx` | 30 bps below 420 SOL market cap. **95 bps** from 420 SOL, falling in steps (70 bps at 9,820 SOL, 30 bps at 49,120 SOL) to **5 bps at ≥ 98,240 SOL**. |

The brief's 0.05% is the bottom tier: PumpSwap coins above about 98,000 SOL
of market cap (about $14.7M at $150). Both are shown below.

The dynamic tiers date from the change described in `docs/FEE_PROGRAM_README.md`
("dynamic fee structure depending on the current market cap"). The exact
values are the on-chain ones above, not the README's image.

**One structural difference matters more than the rates. On pump.fun the
creator is paid on all of their coin's volume, whatever frontend or terminal
routes it.** Terminal share does not reduce it. In a room, the door creator
loses the fraction `s`.

Lifetime volume of real pump.fun coins could not be verified: no public
per-coin distribution was found. These volume paths are illustrations.

| own coin | lifetime volume (assumed) | creator fees, on-chain schedule | at 0.05% (brief) |
|---|---|---|---|
| doesn't run, dies on the curve | $2k / $10k / $30k | $6 / $30 / $90 | $1 / $5 / $15 |
| runs to $1M peak market cap | $1M | $8.7k (PumpSwap blended 89 bps) | $500 |
| runs to $10M peak | $10M | $73.8k (blended 74 bps) | $5.0k |
| runs to $50M peak | $50M | $289.5k (blended 58 bps) | $25.0k |

"Blended" means:

- PumpSwap volume is spread evenly in log market cap from 420 SOL to the peak;
- each slice pays the tier in force at that market cap;
- the first $30k of volume is assumed to trade on the curve.

**Same traders, two venues.** Per $1M of volume generated by the creator's own
community:

| s | door, 0.30% × (1 − s) | own coin on the curve, 30 bps | own coin on PumpSwap at 95 / 30 / 5 bps |
|---|---|---|---|
| 30% | $2,100 | $3,000 | $9,500 / $3,000 / $500 |
| 60% | $1,200 | $3,000 | $9,500 / $3,000 / $500 |
| 90% | $300 | $3,000 | $9,500 / $3,000 / $500 |

At every substitution level above zero, the door pays the creator less than
the pump.fun bonding curve does for the same traders: 70%, 40% and 10% as
much. It pays 3–22% of PumpSwap's 95 bps tier. It beats pump.fun only against
PumpSwap's lowest tiers: above 68,770 SOL of market cap (the 20 bps tier) when
s = 30%, and above 88,400 SOL (10 bps) when s = 60%. Opening the door also costs $76. Launching on pump.fun
costs no door fee; pump.fun's own launch cost was not verified here.

**What the room adds for a non-founder: almost nothing they can collect.** The
room's volume from other doors goes to those doors and to terminals. A
non-founder collects only on traders they bring, plus a uniform-picking
residual: $0.75–262 gross across the table above. A deeper room might make the
creator's own traders trade more; nothing here measures that.

## 4. The room founder

| room volume | founder share, 0.10% of all volume | door-fee share (20 doors × 0.05 SOL) | value to the founder of reserve retirement, at 1% of supply | total, before door-0 fees and the first buy |
|---|---|---|---|---|
| $1M | $1.0k | $150 | $28 | $1.2k |
| $10M | $10.0k | $150 | $208 | $10.4k |
| $50M | $50.0k | $150 | $1.0k | $51.2k |

**Terminal substitution doesn't touch the founder share.** It is paid on every
trade through every door, router doors included.

**Reserve retirement is worth little to the founder.** The reserve share of
trade fees and door fees retires curve position and raises price for all
holders pro rata. A founder holding 1% of supply gets 1% of it.

The founder also owns door 0, and so earns the door-creator income in §2 on
whatever flow door 0 receives.

## 5. First buy: the founder gets the only floor

Price multiple from the entry reserve to a later reserve level, on curve C1.
These are marginal prices, for a small position that exits at that level.

| entry reserve | to $100k | to $1M | to $10M |
|---|---|---|---|
| $0 (founder, the floor) | 67.7× | 222.8× | 707.4× |
| $10k | 6.5× | 21.5× | 68.1× |
| $100k | — | 3.3× | 10.4× |
| $1M | — | — | 3.2× |

This upside belongs to whoever buys at that reserve, not to door creators as
such: anyone can buy the room token without opening a door. Only the founder
buys at the floor. On pump.fun, every creator buys at the floor of their own
coin.

## 6. Answers

**(a) Is opening a door ever worth it for someone who isn't the founder?**

**No.**

- On its own fee income, a door can cover its $76 cost, but only if the
  creator's own traders route $36k–$255k through it (s = 30–90%).
- Those same traders, trading the creator's own pump.fun coin, pay the
  creator more at every substitution level above zero: 1.4× more at s = 30%,
  2.5× at 60% and 10× at 90% on the bonding curve, and up to 32× more in
  PumpSwap's 95 bps tier.
- A pump.fun creator also keeps the floor of their own curve, which a
  non-founder door never gets.
- A door that brings no traders loses money in every room under $50M of
  lifetime volume. Its only income is the assumed uniform-picking residual.
- The room's other volume pays other doors, terminals, the founder and the
  protocol, not the joiner.

The only case where the door wins is against pump.fun's lowest PumpSwap tiers:
coins above 68,770 SOL of market cap at s = 30%, or above 88,400 SOL at
s = 60%. By then the
coin has already run, so it is not a reason to open a door instead of
launching.

**(b) Does founding a room beat joining one, and by how much?**

**Yes, by a wide margin.**

- **Fees.** The founder earns 0.10% of *all* room volume, unaffected by
  substitution: $10.4k on a $10M room against $554 net for a joiner bringing
  5% of volume at s = 60%. That is **about 19×**.
- **When a joiner could match it.** A joiner's door out-earns the founder
  share only if their own traders generate more than `1/(3(1 − s))` of all
  room volume: 48% at s = 30%, 83% at s = 60%. At s = 90% it is impossible.
- **First buy.** The founder buys at the floor: 222.8× to $1M of reserve.
  Joiners pay the room's current price: 21.5× from $10k, 3.3× from $100k.
- **Door 0.** The founder also gets the same door-creator income as any
  joiner, on door 0.

## Limits

- **Terminal substitution is unmeasured.** The public split of pump.fun volume
  by terminal was not found.
- **Other inputs are assumed.** The community share `a`, the uniform-picking
  share ρ, the door count and all pump.fun coin volume paths are assumptions.
- **No behavioural response is modelled.** In particular, nothing tests
  whether a shared room grows the volume a creator's own traders generate.
- **Two figures are measured.** The on-chain pump.fun fee schedule and the
  doors fee defaults are exact. Everything else is a parameter.
