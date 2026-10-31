# Graduation via a transfer-fee canonical token: does the lever exist?

> **Context changed.** This document was written under the earlier ruling that
> v1 does not graduate, and it uses the superseded 30% / founder / reserve /
> protocol split. The current build spec
> ([PERMANENT_CURVE_SPEC.md](PERMANENT_CURVE_SPEC.md)) graduates into Meteora
> DAMM v2 with no transfer fee and a 60/40 split. The source and on-chain
> findings about Token-2022 TransferFee support are unaffected.


31 October 2026. Document only; nothing is built. Ruling 2 stands: v1 does not
graduate. This costs the later option.

**The setup.**

1. A room graduates by putting one canonical room token into an external pool.
2. Door mints are convertible 1:1 to that token.
3. Anyone can then trade the canonical token directly on the pool and skip
   every door and room fee.

The only lever that taxes that bypass is a Token-2022 **TransferFee** on the
canonical token. This document checks whether the lever exists, what it costs,
and what it earns.

**How claims were verified.**

- Program source, pinned to the commits in the table below.
- Live mainnet RPC (`api.mainnet-beta.solana.com`), slot numbers given.
- The DexScreener API, fetched through the session's web tool.

**What could not be reached.** Jupiter's docs (`dev.jup.ag`, `station.jup.ag`)
and the DexScreener web page both failed DNS resolution in this environment.
Claims that depend on them are marked unverified.

| source | commit |
|---|---|
| solana-program/token-2022 | `986b3aa58cbcc40dea12b369912017a4066804e7` |
| raydium-io/raydium-cp-swap (CPMM) | `f4b9b26342afe9122d5ff67cd7a4f19ded4ac0a5` |
| raydium-io/raydium-clmm | `6d7a0f82d2f293c553c69aaf943377367c6c4cc6` |
| raydium-io/raydium-amm (AMM v4) | `91739d8d9f5cf347e0ce14ebe4d2bb7069fb31b6` |
| orca-so/whirlpools | `cc683ec92acb5e7606caa3d8e514d9383e9c7c11` |
| MeteoraAg/damm-v2 (cp-amm) | `5398b5c7c534de014091132da37c6478cce671a8` |
| MeteoraAg/dlmm-sdk (SDK only; no program source) | `af36dd53ab180783ccecda306926189a4700953c` |
| jup-ag/jupiter-amm-interface | `70f56e0495b7c818e4c38e37b2007656892ca2a1` |
| anza-xyz/agave | `aec3b701cfd1ab2c636675b0e30544c60068b08f` |

Source links take the form
`https://github.com/<repo>/blob/<commit>/<path>#L<line>`, using the paths and
lines below.

**The live test case** is BERN, `CKfatsPMUf8SkiURsDXs7eK6GWb4Jsd6UDbs7twMCWxo`.
At slot 463,692,562 it was a Token-2022 mint with `transferFeeBasisPoints: 269`,
`maximumFee: 3906250000000000000`, and a config/withdraw authority of
`BeRNwDN8…FyEe` (`getAccountInfo`, jsonParsed). The on-chain evidence is
`outputs/onchain/*.json`, produced by
`scripts/onchain/run_onchain_checks.sh`.

---

## 1. Which AMMs accept a Token-2022 mint with TransferFee, by pool type

| program | pool type | accepts TransferFee? | permissionless? | fee handled in the math | evidence |
|---|---|---|---|---|---|
| Raydium CPMM `CPMMoo8L…qKP1C` | constant product | **yes** | yes (allowlist in code) | swap in and out, deposit, withdraw | `programs/cp-swap/src/utils/token.rs` L335–360 (`is_supported_mint`: TransferFeeConfig, MetadataPointer, TokenMetadata, InterestBearingConfig, ScaledUiAmount; any other extension needs an admin "support mint" account); `instructions/swap_base_input.rs` L86, L144; `swap_base_output.rs` L23, L81; `deposit.rs` L117, L127; `withdraw.rs` L131, L142 |
| Raydium CLMM `CAMMCzo5…rWqK` | concentrated liquidity | **yes** | yes | positions and swaps | `programs/amm/src/util/token.rs` L436–460 (same allowlist); `instructions/open_position.rs` L422, L442 |
| Raydium AMM v4 `675kPX9M…1Mp8` | legacy constant product | **no** | — | — | No Token-2022 reference anywhere in `program/src`; the processor checks `spl_token::id()` (`processor.rs` L690, L1111, L1431) |
| Orca Whirlpools `whirLbMi…tyCc` | concentrated liquidity (v2 instructions) | **yes** | yes, *if the mint has no freeze authority*; otherwise a TokenBadge is needed | yes | `programs/whirlpool/src/util/v2/token.rs` L208 (`is_supported_token_mint`), L240 (`TransferFeeConfig => {}`) |
| Meteora DAMM v2 `cpamdpZC…sGG` | constant product | **yes** | yes | yes | `programs/cp-amm/src/utils/token.rs` L223–260 (`is_permissionless_supported_mint`: TransferFeeConfig, MetadataPointer, TokenMetadata) |
| Meteora DLMM `LBUZKhRx…wxo` | bin liquidity | **yes in practice; acceptance rules unverifiable** | **unverified**: the IDL has `initialize_token_badge` | SDK quotes net of the fee | Program source is not in the public repo checked. The SDK deducts transfer fees (`commons/src/quote.rs` L469, L533; `commons/src/token_2022.rs` L135–180). On-chain: pool `A2cPP7kqbg84LinFoQ9644dND4Rr6h8gjHdtVDyJ3rdo`, a BERN pair, is owned by the DLMM program (slot 463,694,919). |
| FluxBeam `FLUXubRm…rm1X` | constant product | yes in practice | **unverified** (source not checked) | unverified | BERN's largest pair on DexScreener, `Ebbpz3PW…wLsk`, $404,767 liquidity, is owned by FluxBeam (slot 463,694,921) |
| PumpSwap `pAMMBay6…EXA` | constant product | **not verified** | — | — | Not checked in source. It appears in 1 of 42 sampled BERN transactions, which may be another leg of a multi-hop route. |

Notes:

- **The canonical token must not carry other extensions.** The doors spec gives
  door mints PermissionedBurn. That extension is *not* on any of these
  allowlists. Raydium would need an admin allowlist entry and Orca a badge.
  Meteora DAMM v2 rejects it outright: its whitelist is a closed match with
  `_ => return Ok(false)`.
- **No freeze authority.** Orca rejects a mint with a freeze authority unless
  it has a badge.

## 2. Jupiter

**Routes fee-bearing mints: yes, verified on-chain for BERN.**
`outputs/onchain/bern_program_mix.json` samples 42 successful transactions
touching BERN between slots 463,359,063 and 463,664,217. Six of them invoke
Jupiter v6 (`JUP6LkbZ…TaV4`). The pool programs in the same sample were Meteora
DAMM v2 (22), Raydium CPMM (1), Raydium AMM v4 (1, necessarily a non-BERN leg)
and PumpSwap (1).

**Quotes net of the fee: verified for sells of the fee-bearing token only.**
`outputs/onchain/bern_jupiter_quotes.json` decodes six exact-in Jupiter routes
(`route` and `shared_accounts_route`) that sold BERN:

- In every one, the pool was credited exactly `sent − ceil(2.69% × sent)`. For
  example, 177,476 sent and 172,701 credited; 12,479 sent and 12,143 credited.
- In the three whose output was an SPL token (USDC), the user received
  **exactly** `quoted_out` (2,092; 19; 19,948). That was with
  `slippage_bps = 100`, which is less than the 269 bps fee.
- A quote that ignored the fee would have come in 2.69% short and failed the
  1% slippage check. So these quotes already deducted the input transfer fee.
- The other three paid out native SOL, which token balances don't show, so
  they couldn't be compared.

**Not verified:**

- **Buys**, where the fee is charged on the output transfer to the user. The
  six buy-side Jupiter instructions in the sample use `route_v2` (discriminator
  `bb64facc31c4af14`), whose argument layout I did not decode rather than
  guess.
- **Jupiter's listing or "strict" policy** towards fee-bearing mints, and
  especially towards mints with a live fee authority.
- **Any documentation statement**: Jupiter's docs did not resolve from this
  environment.

The public `jupiter-amm-interface` passes the clock epoch to AMM adapters
(`interface/src/lib.rs` L337–341). Epoch-dependent fees need it, but
fee handling lives in each adapter and in Jupiter's closed router. Nothing in
the public crate is specific to transfer fees.

## 3. DexScreener

`https://api.dexscreener.com/latest/dex/tokens/CKfats…MCWxo` returned 9 pairs
for BERN: 3 on FluxBeam and 6 on Meteora (DLMM and DAMM v2). Each had a
`priceUsd`; the largest showed $404,767 of liquidity. So DexScreener indexes
and prices pools of a fee-bearing Token-2022 mint.

The response has **no transfer-fee field**. Whether DexScreener's price or
volume is net or gross of the fee, and whether its web page warns about the
fee, could not be verified: `dexscreener.com` did not resolve here.

## 4. What the transfer fee does to LPs

These mechanics are from Token-2022 and Raydium CPMM source:

- **Who pays.** The recipient is credited `amount − fee`. The fee is withheld
  inside the *recipient's* token account (token-2022
  `program/src/processor.rs` ~L575–586). The fee is
  `min(ceil(amount·bps/10⁴), maximum_fee)` (`interface/src/extension/transfer_fee/mod.rs` L58).
- **On deposit,** CPMM grosses up the LP's transfer by the inverse fee, so the
  vault receives the intended amount (`deposit.rs` L117, L127). **The LP pays
  the fee on the token side of every deposit.**
- **On withdrawal,** the LP receives `amount − fee` (`withdraw.rs` L131, L142).
  **The LP pays it again.**
- **On each swap,** the trader pays it on the fee-bearing leg: into the vault
  on a sell, out to the trader on a buy. CPMM computes the swap on the
  post-fee input (`swap_base_input.rs` L86).
- LP trading-fee income accrues inside the vault, so it pays no transfer fee
  until withdrawal.

LP round trip, from `outputs/transfer_fee_model.md`, on a $10k position held
half in the token:

| transfer fee | round-trip cost | turnover needed to repay it, if LPs keep an illustrative 25 bps per swap |
|---|---|---|
| 10 bps | $10 | 0.4× TVL |
| 30 bps | $30 | 1.2× TVL |
| 50 bps | $50 | 2.0× TVL |
| 100 bps | $100 | 4.0× TVL |

**Is LPing uneconomic?** Not by itself at these rates. A pool turning over its
TVL a few times during an LP's holding period repays it. The larger effect is
indirect: every swap costs traders the fee on top of the pool fee, so volume
and LP income fall. A graduation pool seeded by the room with burned LP
doesn't depend on third-party LPs at all.

## 5. What it does to ordinary wallet-to-wallet sends

- **Every send is taxed.** Every `TransferChecked` charges the fee, and the
  recipient gets less than was sent.
- **Unchecked `Transfer` fails** on fee-bearing accounts with
  `MintRequiredForTransfer` (`processor.rs` L450–456). Any wallet, bot or
  program still using it breaks.
- **Accounts with withheld fees can't be closed** until someone harvests
  them (`processor.rs` ~L1404, `transfer_fee_state.closable()`). Users
  reclaiming rent on such accounts depend on a harvest first. Harvesting is
  permissionless.
- **Exchange deposits arrive short.** Whether specific exchanges or custodians
  accept the token was not verified.
- **The doors themselves pay too.** Converting door ↔ canonical through a
  wrapper vault is a transfer of the canonical token, so holders pay the fee
  on each conversion.

## 6. Fee limits, authority, rate changes and harvesting

| item | fact | source |
|---|---|---|
| maximum rate | `MAX_FEE_BASIS_POINTS = 10_000` (100%) | `interface/src/extension/transfer_fee/mod.rs` L26 |
| cap per transfer | `maximum_fee: u64`, absolute, in token base units | same file, `TransferFee` struct L34–42 |
| who changes the rate | `transfer_fee_config_authority`, via `SetTransferFee` | `program/src/extension/transfer_fee/processor.rs` L64 onward |
| when a change takes effect | Two epochs after it is set ("set two epochs ahead to avoid rug pulls"). An epoch is 432,000 slots (`getEpochInfo`, slot 463,694,922), so the delay is 864,000 slots. The two most recent rates are stored and selected by epoch. | same function; `mod.rs` `get_epoch_fee` |
| freezing the rate | `SetAuthority(TransferFeeConfig → None)` removes the authority, and the rate is then permanent | `program/src/processor.rs` L874 onward |
| collecting fees | `WithdrawWithheldTokensFromMint` / `…FromAccounts`, signed by `withdraw_withheld_authority` | `interface/src/extension/transfer_fee/instruction.rs` L99 onward |
| harvesting | `HarvestWithheldTokensToMint` is **permissionless**, works on frozen accounts, and skips accounts without the extension | `instruction.rs` L124–135; `processor.rs` L195 (no authority account) |

**Where the fees end up.** On pool *sells*, the fee is withheld in the pool
vault: one account. On pool *buys*, it is withheld in **each buyer's own token
account**, so about half the take is scattered across every holder. To collect
it, someone must find those accounts (a scan of every token account for the
mint) and harvest them in batches. Each batch is limited by the 64-account
transaction lock limit (agave `runtime/src/bank.rs` L3847).

The base fee is 5,000 lamports per signature (`getFeeForMessage`, slot
463,694,000). Harvest base fees from `outputs/transfer_fee_model.md`:

| accounts holding withheld fees | transactions | base fees (SOL) |
|---|---|---|
| 1,000 | 17 | 0.000085 |
| 100,000 | 1,667 | 0.008335 |
| 1,000,000 | 16,667 | 0.083335 |

The signatures are cheap. The real cost is enumerating the accounts, plus
priority fees; neither is included.

**The authority dilemma, which cannot be avoided:**

- Keep `transfer_fee_config_authority`, and it can raise the fee to 100% with
  two epochs' notice (864,000 slots; about four days at roughly 0.4 s per slot,
  a slot time not measured here). Scanners and terminals treat a mutable transfer fee as a
  rug vector. How each one treats it was not verified.
- Remove the authority, and the rate is fixed forever. It can't be lowered if
  it starts strangling volume.

## 7. The arithmetic

Per $1M of volume, from `outputs/transfer_fee_model.md`:

- The transfer-fee take is collected **in canonical tokens**.
- "Net in SOL" assumes those tokens are later sold into the same pool, paying
  the fee once more. Price impact of that sale is excluded.
- Door-routed volume after graduation also moves canonical tokens between the
  pool and the program's wrapper vault, so it pays the transfer fee once, plus
  the door program's 100 bps.

| transfer fee | raw-pool volume: room's take | raw pool: net in SOL | door-routed: transfer fee | door-routed: door program fee | door-routed total |
|---|---|---|---|---|---|
| 10 bps | $1,000 | $999 | $1,000 | $10,000 | $11,000 |
| 30 bps | $3,000 | $2,991 | $3,000 | $10,000 | $13,000 |
| 50 bps | $5,000 | $4,975 | $5,000 | $10,000 | $15,000 |
| 100 bps | $10,000 | $9,900 | $10,000 | $10,000 | $20,000 |

The door program fee splits (spec defaults) as $3,000 door creators, $1,000
founder, $2,000 reserve and $4,000 protocol.

**What these numbers mean:**

1. **The transfer fee taxes both routes equally.** It does not make doors
   competitive. After graduation a door is still more expensive than the raw
   pool by exactly the door program fee, 100 bps, at every transfer-fee rate.
   Price-insensitive routing (Jupiter) will keep choosing the raw pool. The
   lever **recovers** `rate × raw volume` for whoever holds the withdraw
   authority. It does not bring volume back to doors, and door creators still
   earn nothing on raw-pool volume.
2. **To match the door fee on bypass volume, the rate must equal it: 100 bps.**
   That is 1% on every swap, LP deposit, LP withdrawal, conversion and wallet
   send, on top of the pool's own fee.
3. **It is not a reserve in the curve sense.** After graduation there is no
   room curve. The liquidity is in the external pool. The take arrives as the
   room's own token, half of it scattered in buyers' accounts. Turning it into
   SOL means selling the room token into the room's own pool: a second fee,
   and sell pressure equal to the take. The alternative, burning it, helps
   holders but adds no SOL anywhere.
4. **It conflicts with how the doors were specified.** Doors that convert 1:1
   into a canonical token traded elsewhere become wrappers for the volume that
   matters. Ruling 3 excludes that design for v1. It also means the canonical
   token cannot carry PermissionedBurn (§1), so the door spec's supply-control
   extension does not carry over.

## Verdict

**Dead as a reserve path:** the lever exists, but it is a flat tax that both routes pay, collected in the room's own token, that never brings flow back to doors.
