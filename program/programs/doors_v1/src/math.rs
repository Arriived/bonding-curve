use crate::Error;
use anchor_lang::prelude::*;
pub const U: u64 = 1_000_000_000_000_000;
pub fn add(a: u64, b: u64) -> Result<u64> {
    a.checked_add(b).ok_or(error!(Error::Overflow))
}
pub fn sub(a: u64, b: u64) -> Result<u64> {
    a.checked_sub(b).ok_or(error!(Error::Balance))
}
pub fn narrow(v: u128) -> Result<u64> {
    u64::try_from(v).map_err(|_| error!(Error::Overflow))
}
pub fn reserve(vs: u64, vt: u64, q: u64) -> Result<u64> {
    require!(q <= U && vt > q, Error::Balance);
    narrow((vs as u128).checked_mul(q as u128).ok_or(Error::Overflow)? / (vt - q) as u128)
}
pub fn inverse(vs: u64, vt: u64, r: u64) -> Result<u64> {
    let k = (vs as u128)
        .checked_mul(vt as u128)
        .ok_or(Error::Overflow)?;
    let denom = (r as u128)
        .checked_add(vs as u128)
        .and_then(|n| n.checked_add(1))
        .ok_or(Error::Overflow)?;
    let q = (vt as u128)
        .checked_sub(k / denom)
        .and_then(|n| n.checked_sub(1))
        .ok_or(Error::Balance)?;
    let q = narrow(q)?;
    require!(q <= U, Error::Balance);
    Ok(q)
}
pub fn ratio(n: u64, bps: u16, ceil: bool) -> Result<u64> {
    narrow(((n as u128) * (bps as u128) + if ceil { 9999 } else { 0 }) / 10000)
}
pub fn buy_amounts(gross: u64, bps: u16, available: u64) -> Result<(u64, u64)> {
    require!(gross > 0, Error::Amount);
    let net = narrow((gross as u128) * 10000 / (10000 + bps as u128))?;
    if net > available {
        Ok((available, ratio(available, bps, true)?))
    } else {
        Ok((net, sub(gross, net)?))
    }
}

pub const DOOR_VIRTUAL_BASE: u64 = 1_073_025_606_000_000;
const DOOR_QUOTE_LAMPORTS: u64 = 30_000_000_000;

// Floor the room-token amount represented by the SOL anchor at the room spot.
// Split the fraction before multiplying to cover the full configured price range.
pub fn door_virtual_quote(price_num: u128, price_den: u128) -> Result<u128> {
    require!(price_num > 0, Error::Invariant);
    let scale = u128::from(DOOR_QUOTE_LAMPORTS);
    let whole = (price_den / price_num)
        .checked_mul(scale)
        .ok_or(Error::Overflow)?;
    let remainder = price_den % price_num;
    let fraction = if let Some(product) = remainder.checked_mul(scale) {
        product / price_num
    } else {
        // Compute the integer quotient of remainder * scale without a wide
        // intermediate product. Each step keeps the residual below price_num.
        let mut quotient = 0;
        let mut residual = 0;
        for bit in (0..(u64::BITS - DOOR_QUOTE_LAMPORTS.leading_zeros())).rev() {
            quotient *= 2;
            if residual >= price_num - residual {
                residual -= price_num - residual;
                quotient += 1;
            } else {
                residual *= 2;
            }
            if (DOOR_QUOTE_LAMPORTS >> bit) & 1 != 0 {
                if residual >= price_num - remainder {
                    residual -= price_num - remainder;
                    quotient += 1;
                } else {
                    residual += remainder;
                }
            }
        }
        quotient
    };
    Ok(whole.checked_add(fraction).ok_or(Error::Overflow)?.max(1))
}

pub fn door_integral(virtual_quote: u128, sold: u64) -> Result<u64> {
    require!(virtual_quote > 0 && sold <= U, Error::Invariant);
    let numerator = virtual_quote
        .checked_mul(u128::from(sold))
        .ok_or(Error::Overflow)?;
    narrow(numerator / u128::from(DOOR_VIRTUAL_BASE - sold))
}

pub fn door_advance(virtual_quote: u128, sold: u64, room_tokens: u64) -> Result<u64> {
    let target = u128::from(add(door_integral(virtual_quote, sold)?, room_tokens)?) + 1;
    // Algebraic form of the room inverse with one base unit of rounding slack.
    let next = (target * u128::from(DOOR_VIRTUAL_BASE) - 1) / (virtual_quote + target);
    require!(next <= u128::from(U), Error::DoorSupplyExhausted);
    narrow(next)
}
