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
    narrow(
        (vs as u128)
            .checked_mul(vt as u128)
            .ok_or(Error::Overflow)?
            / (vt - q) as u128,
    )?
    .checked_sub(vs)
    .ok_or(error!(Error::Overflow))
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
