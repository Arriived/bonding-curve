use crate::{math::*, Error};
use anchor_lang::prelude::*;

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug)]
pub struct Settings {
    pub protocol_fee_recipient: Pubkey,
    pub fee_bps: u16,
    pub door_share_bps: u16,
    pub door_fee_lamports: u64,
    pub room_fee_lamports: u64,
    pub convert_fee_lamports: u64,
    pub v_sol_lamports: u64,
    pub v_tok: u64,
    pub supply: u64,
    pub r_star_lamports: u64,
    pub meteora_dynamic_config: Pubkey,
    pub graduation_trigger_lamports: u64,
    pub paused: bool,
    pub matcher_authority: Pubkey,
    pub live_min_reserve_lamports: u64,
    pub live_max_idle_seconds: u64,
    pub live_new_seconds: u64,
    pub live_min_volume_lamports: u64,
    pub pool_min_window_lp_fee: u64,
    pub founder_share_bps: u16,
}
impl Settings {
    pub fn validate(&self) -> Result<()> {
        require!(
            self.fee_bps < 10_000
                && self.door_share_bps as u32 + self.founder_share_bps as u32 <= 10_000,
            Error::BadConfig
        );
        require!(
            self.supply == U && self.v_tok > U && self.v_sol_lamports > 0,
            Error::BadConfig
        );
        require!(
            self.graduation_trigger_lamports >= self.r_star_lamports && self.r_star_lamports > 0,
            Error::BadConfig
        );
        require!(
            self.protocol_fee_recipient != Pubkey::default()
                && self.matcher_authority != Pubkey::default(),
            Error::BadConfig
        );
        require!(
            self.room_fee_lamports
                .checked_add(self.door_fee_lamports)
                .is_some(),
            Error::BadConfig
        );
        // The cap must permit a positive purchase. Quotes up to this sold
        // amount are monotonic and bounded by the representable trigger.
        let q = inverse(
            self.v_sol_lamports,
            self.v_tok,
            self.graduation_trigger_lamports,
        )
        .map_err(|_| error!(Error::BadConfig))?;
        require!(q > 0 && q <= U, Error::BadConfig);
        require!(
            reserve(self.v_sol_lamports, self.v_tok, q).map_err(|_| error!(Error::BadConfig))?
                <= self.graduation_trigger_lamports,
            Error::BadConfig
        );
        Ok(())
    }
}

#[account]
pub struct Config {
    pub admin: Pubkey,
    pub protocol_fee_recipient: Pubkey,
    pub fee_bps: u16,
    pub door_share_bps: u16,
    pub door_fee_lamports: u64,
    pub room_fee_lamports: u64,
    pub convert_fee_lamports: u64,
    pub v_sol_lamports: u64,
    pub v_tok: u64,
    pub supply: u64,
    pub r_star_lamports: u64,
    pub meteora_dynamic_config: Pubkey,
    pub graduation_trigger_lamports: u64,
    pub paused: bool,
    pub bump: u8,
    pub matcher_authority: Pubkey,
    pub live_min_reserve_lamports: u64,
    pub live_max_idle_seconds: u64,
    pub live_new_seconds: u64,
    pub live_min_volume_lamports: u64,
    pub pool_min_window_lp_fee: u64,
    pub founder_share_bps: u16,
}
impl Config {
    pub const LEN: usize = 248;
    // Only immutable room economics are bound here. Flat fees have their own
    // signed maximum, and operational settings remain administratively mutable.
    pub fn launch_terms_hash(&self) -> [u8; 32] {
        solana_sha256_hasher::hashv(&[
            b"doors-v1:launch-terms:v1",
            &self.v_sol_lamports.to_le_bytes(),
            &self.v_tok.to_le_bytes(),
            &self.supply.to_le_bytes(),
            &self.r_star_lamports.to_le_bytes(),
            &self.graduation_trigger_lamports.to_le_bytes(),
            &self.fee_bps.to_le_bytes(),
            &self.door_share_bps.to_le_bytes(),
            &self.founder_share_bps.to_le_bytes(),
        ])
        .to_bytes()
    }
    pub fn apply(&mut self, s: Settings) -> Result<()> {
        s.validate()?;
        self.protocol_fee_recipient = s.protocol_fee_recipient;
        self.fee_bps = s.fee_bps;
        self.door_share_bps = s.door_share_bps;
        self.door_fee_lamports = s.door_fee_lamports;
        self.room_fee_lamports = s.room_fee_lamports;
        self.convert_fee_lamports = s.convert_fee_lamports;
        self.v_sol_lamports = s.v_sol_lamports;
        self.v_tok = s.v_tok;
        self.supply = s.supply;
        self.r_star_lamports = s.r_star_lamports;
        self.meteora_dynamic_config = s.meteora_dynamic_config;
        self.graduation_trigger_lamports = s.graduation_trigger_lamports;
        self.paused = s.paused;
        self.matcher_authority = s.matcher_authority;
        self.live_min_reserve_lamports = s.live_min_reserve_lamports;
        self.live_max_idle_seconds = s.live_max_idle_seconds;
        self.live_new_seconds = s.live_new_seconds;
        self.live_min_volume_lamports = s.live_min_volume_lamports;
        self.pool_min_window_lp_fee = s.pool_min_window_lp_fee;
        self.founder_share_bps = s.founder_share_bps;
        Ok(())
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default)]
pub struct Bucket {
    pub start: i64,
    pub amount: u128,
}

// Exact marginal curve price in lamports per token base unit. No division or
// floating-point conversion is needed to report it to terminals and indexers.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy)]
pub struct Price {
    pub numerator: u128,
    pub denominator: u128,
}

#[account]
pub struct Room {
    pub room_id: u64,
    pub bumps: [u8; 7],
    pub status: u8,
    pub room_mint: Pubkey,
    pub room_vault: Pubkey,
    pub retired_vault: Pubkey,
    pub fee_wsol: Pubkey,
    pub v_sol_lamports: u64,
    pub v_tok: u64,
    pub supply: u64,
    pub r_star_lamports: u64,
    pub graduation_trigger_lamports: u64,
    pub fee_bps: u16,
    pub door_share_bps: u16,
    pub reserve: u64,
    pub sold: u64,
    pub retired: u64,
    pub door_count: u32,
    pub protocol_accrued_sol: u64,
    pub protocol_accrued_wsol: u64,
    pub pending_reserve_sol: u64,
    pub pending_reserve_wsol: u64,
    pub reserve_share_total: u64,
    pub volume_gross: u128,
    pub trades: u64,
    pub created_at: i64,
    pub last_trade_at: i64,
    pub graduated_at: i64,
    pub damm_pool: Pubkey,
    pub damm_position: Pubkey,
    pub position_nft_mint: Pubkey,
    pub identity: [u8; 32],
    pub uri_len: u8,
    pub uri: [u8; 200],
    pub fee_ckpt: u128,
    pub fee_ckpt_ts: i64,
    pub liveness_buckets: [Bucket; 25],
    pub founder: Pubkey,
    pub founder_accrued: u64,
    pub founder_accrued_wsol: u64,
    pub founder_share_bps: u16,
}
impl Room {
    pub const LEN: usize = 1315;
    pub fn curve(&self, q: u64) -> Result<u64> {
        reserve(self.v_sol_lamports, self.v_tok, q)
    }
    pub fn price(&self) -> Result<Price> {
        let numerator = (self.v_sol_lamports as u128)
            .checked_mul(self.v_tok as u128)
            .ok_or(Error::Overflow)?;
        let remaining = sub(self.v_tok, self.sold)? as u128;
        let denominator = remaining.checked_mul(remaining).ok_or(Error::Overflow)?;
        require!(denominator > 0, Error::Invariant);
        Ok(Price {
            numerator,
            denominator,
        })
    }
    pub fn advance(&self, n: u64) -> Result<u64> {
        inverse(
            self.v_sol_lamports,
            self.v_tok,
            add(self.curve(self.sold)?, n)?,
        )
    }
    pub fn live(&self, c: &Config, now: i64) -> Result<bool> {
        // Status 2 cannot be created by v1. Fail closed until the pool adapter exists.
        require!(self.status <= 1, Error::PhaseTwo);
        if self.created_at > now {
            return Ok(false);
        }
        if ((now - self.created_at) as u64) < c.live_new_seconds {
            return Ok(true);
        }
        if self.last_trade_at > now {
            return Ok(false);
        }
        let volume = self
            .liveness_buckets
            .iter()
            .filter(|b| {
                b.start % 3600 == 0 && b.start >= now.saturating_sub(86400) && b.start <= now
            })
            .try_fold(0u128, |n, b| {
                n.checked_add(b.amount).ok_or(error!(Error::Overflow))
            })?;
        Ok(self.reserve >= c.live_min_reserve_lamports
            && (now - self.last_trade_at) as u64 <= c.live_max_idle_seconds
            && volume >= c.live_min_volume_lamports as u128)
    }
    pub fn record(&mut self, now: i64, gross: u64) -> Result<()> {
        require!(now >= 0, Error::Clock);
        self.volume_gross = self
            .volume_gross
            .checked_add(gross as u128)
            .ok_or(Error::Overflow)?;
        self.trades = add(self.trades, 1)?;
        self.last_trade_at = now;
        let start = now / 3600 * 3600;
        let b = &mut self.liveness_buckets[(start / 3600 % 25) as usize];
        if b.start != start {
            *b = Bucket { start, amount: 0 };
        }
        b.amount = b.amount.checked_add(gross as u128).ok_or(Error::Overflow)?;
        Ok(())
    }
    pub fn split(&mut self, fee: u64, door: Option<&mut Door>) -> Result<()> {
        let d = ratio(fee, self.door_share_bps, false)?;
        let f = ratio(fee, self.founder_share_bps, false)?;
        let p = sub(sub(fee, d)?, f)?;
        require!(add(add(d, f)?, p)? == fee, Error::Invariant); // F1, exact remainder to protocol
        if let Some(door) = door {
            door.accrued_sol = add(door.accrued_sol, d)?;
        } else {
            self.pending_reserve_sol = add(self.pending_reserve_sol, d)?;
        }
        self.founder_accrued = add(self.founder_accrued, f)?;
        self.protocol_accrued_sol = add(self.protocol_accrued_sol, p)?;
        Ok(())
    }
}
#[account]
pub struct Door {
    pub room: Pubkey,
    pub index: u32,
    pub mint: Pubkey,
    pub door_vault: Pubkey,
    pub room_token_vault: Pubkey,
    pub creator: Pubkey,
    pub fee_recipient: Pubkey,
    pub bumps: [u8; 4],
    pub backing: u64,
    pub accrued_sol: u64,
    pub accrued_wsol: u64,
    pub claimed_sol: u64,
    pub claimed_wsol: u64,
    pub buy_volume: u128,
    pub sell_volume: u128,
    pub trades: u64,
    pub created_at: i64,
    pub matcher_version: u16,
    pub rule: u8,
    pub face: u32,
    pub reserved: [u8; 25],
}
impl Door {
    pub const LEN: usize = 328;
}
#[account]
pub struct SlugLock {
    pub room_id: u64,
    pub bump: u8,
}
impl SlugLock {
    pub const LEN: usize = 17;
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct Launch {
    pub name: String,
    pub symbol: String,
    pub uri: String,
    pub first_buy_lamports: u64,
    pub min_tokens_out: u64,
    pub matcher_version: u16,
    pub rule: u8,
    pub face: u32,
    // Total flat protocol fee, excluding the separately bounded first buy
    // and account rent. Included in both launcher and matcher signatures.
    pub max_fee_lamports: u64,
    // Required by create_room; open_door uses its room's immutable snapshot.
    pub expected_terms_hash: [u8; 32],
}
impl Launch {
    pub fn validate(&self) -> Result<()> {
        require!(
            !self.name.is_empty()
                && self.name.len() <= 32
                && !self.symbol.is_empty()
                && self.symbol.len() <= 10
                && self.uri.len() <= 200,
            Error::Metadata
        );
        require!(self.matcher_version > 0 && self.rule <= 4, Error::Metadata);
        Ok(())
    }
    pub fn identity(&self) -> [u8; 32] {
        solana_sha256_hasher::hashv(&[
            &fold(self.symbol.as_bytes()),
            &[0],
            &fold(self.name.as_bytes()),
        ])
        .to_bytes()
    }
}
pub fn fold(input: &[u8]) -> Vec<u8> {
    if !input.is_ascii() {
        return input
            .iter()
            .filter_map(|&c| {
                let c = match c {
                    b'0' => b'O',
                    b'1' => b'I',
                    b'3' => b'E',
                    b'4' => b'A',
                    b'5' => b'S',
                    b'7' => b'T',
                    b'8' => b'B',
                    _ => c.to_ascii_uppercase(),
                };
                (c >= 128 || c.is_ascii_alphanumeric()).then_some(c)
            })
            .collect();
    }
    let a: Vec<u8> = input.iter().map(|c| c.to_ascii_lowercase()).collect();
    let mut out = Vec::with_capacity(a.len());
    let mut i = 0;
    while i < a.len() {
        let (c, step) = if a.get(i..i + 2) == Some(b"rn") {
            (b'm', 2)
        } else if a.get(i..i + 2) == Some(b"vv") {
            (b'w', 2)
        } else {
            (a[i], 1)
        };
        let c = match c {
            b'0' => b'O',
            b'1' => b'I',
            b'3' => b'E',
            b'4' => b'A',
            b'5' => b'S',
            b'7' => b'T',
            b'8' => b'B',
            _ => c.to_ascii_uppercase(),
        };
        if c >= 128 || c.is_ascii_alphanumeric() {
            out.push(c);
        }
        i += step;
    }
    out
}
