use crate::{math::*, state::*, vaults::*, Error, Trade};
use anchor_lang::prelude::*;
pub struct DoorRoute<'a, 'info> {
    pub d: &'a mut Door,
    pub authority: AccountInfo<'info>,
    pub mint: AccountInfo<'info>,
    pub vault: AccountInfo<'info>,
    pub backing: AccountInfo<'info>,
}
impl<'a, 'info> DoorRoute<'a, 'info> {
    pub fn new(
        d: &'a mut Door,
        authority: &AccountInfo<'info>,
        mint: &AccountInfo<'info>,
        vault: &AccountInfo<'info>,
        backing: &AccountInfo<'info>,
    ) -> Self {
        Self {
            d,
            authority: authority.clone(),
            mint: mint.clone(),
            vault: vault.clone(),
            backing: backing.clone(),
        }
    }
}
#[allow(clippy::too_many_arguments)]
pub fn execute_trade<'a>(
    r: &mut Room,
    ri: &AccountInfo<'a>,
    mut route: Option<DoorRoute<'_, 'a>>,
    reserve: &AccountInfo<'a>,
    fees: &AccountInfo<'a>,
    room_vault: &AccountInfo<'a>,
    room_mint: &AccountInfo<'a>,
    user: &AccountInfo<'a>,
    user_token: &AccountInfo<'a>,
    tp: &AccountInfo<'a>,
    system: Option<&AccountInfo<'a>>,
    buy: bool,
    input: u64,
    min: u64,
    now: i64,
) -> Result<()> {
    // Until graduation exists, completion is a reversible buy cap. Holders
    // can always redeem on the curve; unsupported pool states still fail.
    require!(r.status <= 1 && (!buy || r.status == 0), Error::PhaseTwo);
    require!(input > 0, Error::Amount);
    let rk = ri.key();
    if let Some(d) = route.as_ref() {
        door_check(d.d, &d.authority, r, rk, &d.mint, &d.vault, &d.backing)?;
    }
    let selected_mint = route.as_ref().map_or(room_mint.key, |d| d.mint.key);
    user_ata(
        user_token,
        user.key,
        selected_mint,
        &spl_token_2022_interface::ID,
    )?;
    let bl = reserve.lamports();
    let br = r.reserve;
    let fl = fees.lamports();
    let fk = known(r, &route.as_ref().map(|d| vec![&*d.d]).unwrap_or_default());
    let rid = r.room_id.to_le_bytes();
    let rb = [r.bumps[0]];
    let rs: &[&[u8]] = &[b"room", &rid, &rb];
    let (tokens, n, f) = if buy {
        let (n, f) = buy_amounts(
            input,
            r.fee_bps,
            sub(r.graduation_trigger_lamports, r.reserve)?,
        )?;
        require!(n > 0, Error::Amount);
        let q = r.advance(n)?;
        let tokens = sub(q, r.sold)?;
        require!(
            tokens > 0 && tokens >= min && tokens <= sub(r.supply, r.sold)?,
            Error::Slippage
        );
        if let Some(d) = route.as_ref() {
            require!(tokens <= sub(r.supply, d.d.backing)?, Error::Balance);
        }
        deposit(user, reserve, system.ok_or(Error::Account)?, n)?;
        deposit(user, fees, system.unwrap(), f)?;
        if let Some(d) = route.as_mut() {
            transfer(
                room_vault,
                room_mint,
                &d.backing,
                ri,
                tp,
                tokens,
                Some(rs),
                6,
            )?;
            let ix = d.d.index.to_le_bytes();
            let b = [d.d.bumps[0]];
            transfer(
                &d.vault,
                &d.mint,
                user_token,
                &d.authority,
                tp,
                tokens,
                Some(&[b"door", rk.as_ref(), &ix, &b]),
                6,
            )?;
            d.d.backing = add(d.d.backing, tokens)?;
        } else {
            transfer(
                room_vault,
                room_mint,
                user_token,
                ri,
                tp,
                tokens,
                Some(rs),
                6,
            )?;
        }
        r.reserve = add(r.reserve, n)?;
        r.sold = q;
        if r.reserve == r.graduation_trigger_lamports {
            r.status = 1;
        }
        (tokens, n, f)
    } else {
        require!(input <= r.sold, Error::Balance);
        let g = sub(r.curve(r.sold)?, r.curve(sub(r.sold, input)?)?)?;
        let f = ratio(g, r.fee_bps, true)?;
        require!(sub(g, f)? >= min, Error::Slippage);
        if let Some(d) = route.as_mut() {
            require!(input <= d.d.backing, Error::Balance);
            transfer(user_token, &d.mint, &d.vault, user, tp, input, None, 6)?;
            let ix = d.d.index.to_le_bytes();
            let b = [d.d.bumps[0]];
            transfer(
                &d.backing,
                room_mint,
                room_vault,
                &d.authority,
                tp,
                input,
                Some(&[b"door", rk.as_ref(), &ix, &b]),
                6,
            )?;
            d.d.backing = sub(d.d.backing, input)?;
        } else {
            transfer(user_token, room_mint, room_vault, user, tp, input, None, 6)?;
        }
        debit(reserve, user, sub(g, f)?)?;
        debit(reserve, fees, f)?;
        require!(bl - reserve.lamports() == g, Error::Invariant); // I3, no fee is extracted in addition to g
        r.reserve = sub(r.reserve, g)?;
        r.sold = sub(r.sold, input)?;
        if r.reserve < r.graduation_trigger_lamports {
            r.status = 0;
        }
        (input, g, f)
    };
    r.split(f, route.as_mut().map(|d| &mut *d.d))?;
    if let Some(d) = route.as_mut() {
        let v = if buy {
            &mut d.d.buy_volume
        } else {
            &mut d.d.sell_volume
        };
        // Quote volume is the buy fee base or gross sell proceeds. Program
        // fees do not count as activity (matcher spec section 8, Room).
        *v = v.checked_add(n as u128).ok_or(Error::Overflow)?;
        d.d.trades = add(d.d.trades, 1)?;
    }
    r.record(now, n)?;
    if let Some(d) = route.as_ref() {
        door_check(d.d, &d.authority, r, rk, &d.mint, &d.vault, &d.backing)?;
    }
    require!(
        r.reserve >= r.curve(r.sold)? && r.sold <= U,
        Error::Invariant
    );
    require!(
        token(room_vault, &r.room_mint, &rk, &spl_token_2022_interface::ID)? >= sub(U, r.sold)?,
        Error::Invariant
    );
    require!(
        reserve.lamports() as i128 - bl as i128 == r.reserve as i128 - br as i128,
        Error::Invariant
    );
    fee_delta(
        fl,
        fees.lamports(),
        fk,
        known(r, &route.as_ref().map(|d| vec![&*d.d]).unwrap_or_default()),
    )?;
    emit!(Trade {
        room: rk,
        door: route.as_ref().map(|d| d.authority.key()),
        user: user.key(),
        buy,
        tokens,
        curve_lamports: n,
        fee: f,
        sold_after: r.sold,
        reserve: r.reserve,
        status: r.status,
        price_after: r.price()?,
    });
    Ok(())
}
