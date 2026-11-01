use anchor_lang::prelude::*;
pub mod contexts;
pub mod math;
pub mod state;
mod trading;
pub mod vaults;
use contexts::*;
use math::*;
use state::*;
use trading::*;
use vaults::*;

declare_id!("DooraBVNQFSS3MDouMCN2Cyd1QPmS8gjTgN4Q1q3wG7v");

#[program]
pub mod doors_v1 {
    use super::*;
    pub fn initialize_config(ctx: Context<InitializeConfig>, settings: Settings) -> Result<()> {
        let c = &mut ctx.accounts.config;
        c.admin = ctx.accounts.admin.key();
        c.bump = ctx.bumps.config;
        c.apply(settings.clone())?;
        emit!(ConfigChanged {
            admin: c.admin,
            matcher: c.matcher_authority,
            founder_share_bps: c.founder_share_bps,
            settings,
        });
        Ok(())
    }
    pub fn update_config(
        ctx: Context<UpdateConfig>,
        settings: Settings,
        new_admin: Pubkey,
    ) -> Result<()> {
        require!(new_admin != Pubkey::default(), Error::Authority);
        let c = &mut ctx.accounts.config;
        c.apply(settings.clone())?;
        c.admin = new_admin;
        emit!(ConfigChanged {
            admin: c.admin,
            matcher: c.matcher_authority,
            founder_share_bps: c.founder_share_bps,
            settings,
        });
        Ok(())
    }
    pub fn create_room(ctx: Context<CreateRoom>, room_id: u64, launch: Launch) -> Result<()> {
        require_top_level_launch()?;
        let a = ctx.accounts;
        launch.validate()?;
        require!(!a.config.paused, Error::Paused);
        let now = Clock::get()?.unix_timestamp;
        // Validate exact-identity floor before any persistent side effect (all CPIs atomic).
        let identity = launch.identity();
        let old = read_slug(&a.slug, &identity)?;
        if let Some(lock) = &old {
            holder_dead(lock, a.old_holder.as_ref(), &a.config, now)?;
        } else {
            require!(a.old_holder.is_none(), Error::Holder);
        }
        let room_info = a.room.to_account_info();
        let rk = a.room.key();
        let rid = room_id.to_le_bytes();
        let rb = [ctx.bumps.room];
        let rs: &[&[u8]] = &[b"room", &rid, &rb];
        let user = a.user.to_account_info();
        let system = a.system_program.to_account_info();
        let tp = a.token_program.to_account_info();
        let reserve_b = create_pda(
            &user,
            &a.reserve,
            &system,
            &crate::ID,
            0,
            0,
            &[b"reserve", rk.as_ref()],
        )?;
        let fee_b = create_pda(
            &user,
            &a.fees,
            &system,
            &crate::ID,
            0,
            0,
            &[b"fees", rk.as_ref()],
        )?;
        let grad_b = create_pda(
            &user,
            &a.grad_payer,
            &system,
            &anchor_lang::system_program::ID,
            0,
            0,
            &[b"grad_payer", rk.as_ref()],
        )?;
        // Separate initial rent/top-up from credited trading liabilities.
        // Prefunded native donations remain unaccounted and locked.
        let reserve_base = a.reserve.lamports();
        let fee_base = a.fees.lamports();
        let (_, rvb) = create_mint(
            &user,
            &a.room_mint,
            &a.room_vault,
            &room_info,
            rk,
            &launch,
            None,
            &system,
            &tp,
            &[b"room_mint", rk.as_ref()],
            &[b"room_vault", rk.as_ref()],
            rs,
        )?;
        let retired_b = create_token(
            &user,
            &a.retired,
            &a.room_mint,
            &rk,
            &system,
            &tp,
            &[b"retired", rk.as_ref()],
        )?;
        let fw_b = create_token(
            &user,
            &a.fee_wsol,
            &a.wsol_mint,
            &rk,
            &system,
            &a.classic_token_program,
            &[b"fee_wsol", rk.as_ref()],
        )?;
        let slug_b = if old.is_none() {
            create_pda(
                &user,
                &a.slug,
                &system,
                &crate::ID,
                SlugLock::LEN,
                SlugLock::LEN,
                &[b"slug", &identity],
            )?
        } else {
            pda(&a.slug, &[b"slug", &identity])?
        };
        SlugLock {
            room_id,
            bump: slug_b,
        }
        .try_serialize(&mut &mut a.slug.try_borrow_mut_data()?[..])?;
        let r = &mut a.room;
        r.room_id = room_id;
        r.bumps = [
            ctx.bumps.room,
            reserve_b,
            fee_b,
            grad_b,
            rvb,
            retired_b,
            fw_b,
        ];
        r.status = 0;
        r.room_mint = a.room_mint.key();
        r.room_vault = a.room_vault.key();
        r.retired_vault = a.retired.key();
        r.fee_wsol = a.fee_wsol.key();
        r.v_sol_lamports = a.config.v_sol_lamports;
        r.v_tok = a.config.v_tok;
        r.supply = a.config.supply;
        r.r_star_lamports = a.config.r_star_lamports;
        r.graduation_trigger_lamports = a.config.graduation_trigger_lamports;
        r.fee_bps = a.config.fee_bps;
        r.door_share_bps = a.config.door_share_bps;
        r.created_at = now;
        r.last_trade_at = now;
        r.identity = identity;
        r.uri_len = launch.uri.len() as u8;
        r.uri[..launch.uri.len()].copy_from_slice(launch.uri.as_bytes());
        r.founder = a.user.key();
        r.founder_share_bps = a.config.founder_share_bps;
        require!(
            r.door_share_bps as u32 + r.founder_share_bps as u32 <= 10000,
            Error::BadConfig
        );
        let door_info = a.door.to_account_info();
        initialize_door(
            r,
            &mut a.door,
            &door_info,
            ctx.bumps.door,
            rk,
            &user,
            &a.door_mint,
            &a.door_vault,
            &a.backing,
            &a.room_mint,
            &launch,
            &system,
            &tp,
            now,
        )?;
        let fee = add(a.config.room_fee_lamports, a.config.door_fee_lamports)?;
        deposit(&user, &a.fees, &system, fee)?;
        r.protocol_accrued_sol = add(r.protocol_accrued_sol, fee)?;
        emit!(RoomCreated {
            room: rk,
            room_id,
            identity,
            founder: r.founder,
            founder_share_bps: r.founder_share_bps,
            matcher_version: launch.matcher_version,
            rule: launch.rule,
            face: launch.face
        });
        if launch.first_buy_lamports > 0 {
            create_user_ata(
                &user,
                &a.user_token,
                &a.door_mint,
                &system,
                &tp,
                &a.associated_token_program,
            )?;
            execute_trade(
                r,
                &room_info,
                Some(DoorRoute::new(
                    &mut a.door,
                    &door_info,
                    &a.door_mint,
                    &a.door_vault,
                    &a.backing,
                )),
                &a.reserve,
                &a.fees,
                &a.room_vault,
                &a.room_mint,
                &user,
                &a.user_token,
                &tp,
                Some(&system),
                true,
                launch.first_buy_lamports,
                launch.min_tokens_out,
                now,
            )?;
        }
        room_check(
            r,
            rk,
            &a.reserve,
            &a.fees,
            &a.room_vault,
            &a.retired,
            &a.room_mint,
            a.door.accrued_sol,
        )?;
        door_check(
            &a.door,
            &door_info,
            r,
            rk,
            &a.door_mint,
            &a.door_vault,
            &a.backing,
        )?;
        require!(
            a.reserve.lamports() == add(reserve_base, r.reserve)?,
            Error::Invariant
        );
        require!(
            a.fees.lamports() == add(fee_base, narrow(known(r, &[&a.door]))?)?,
            Error::Invariant
        );
        Ok(())
    }
    pub fn open_door(ctx: Context<OpenDoor>, launch: Launch) -> Result<()> {
        require_top_level_launch()?;
        let a = ctx.accounts;
        launch.validate()?;
        let now = Clock::get()?.unix_timestamp;
        require!(!a.core.config.paused, Error::Paused);
        require!(a.core.room.live(&a.core.config, now)?, Error::Dead);
        let identity = launch.identity();
        if let Some(lock) = read_slug(&a.slug, &identity)? {
            if lock.room_id != a.core.room.room_id {
                holder_dead(&lock, a.old_holder.as_ref(), &a.core.config, now)?;
            } else {
                require!(a.old_holder.is_none(), Error::Holder);
            }
        } else {
            require!(a.old_holder.is_none(), Error::Holder);
        }
        let before_l = a.core.reserve.lamports();
        let before_r = a.core.room.reserve;
        let fl = a.core.fees.lamports();
        let fk = known(&a.core.room, &[]);
        let ri = a.core.room.to_account_info();
        let rk = ri.key();
        let di = a.door.to_account_info();
        let user = a.user.to_account_info();
        let system = a.system_program.to_account_info();
        let tp = a.token_program.to_account_info();
        initialize_door(
            &mut a.core.room,
            &mut a.door,
            &di,
            ctx.bumps.door,
            rk,
            &user,
            &a.door_mint,
            &a.door_vault,
            &a.backing,
            &a.core.room_mint,
            &launch,
            &system,
            &tp,
            now,
        )?;
        let fee = a.core.config.door_fee_lamports;
        deposit(&user, &a.core.fees, &system, fee)?;
        a.core.room.protocol_accrued_sol = add(a.core.room.protocol_accrued_sol, fee)?;
        if launch.first_buy_lamports > 0 {
            create_user_ata(
                &user,
                &a.user_token,
                &a.door_mint,
                &system,
                &tp,
                &a.associated_token_program,
            )?;
            execute_trade(
                &mut a.core.room,
                &ri,
                Some(DoorRoute::new(
                    &mut a.door,
                    &di,
                    &a.door_mint,
                    &a.door_vault,
                    &a.backing,
                )),
                &a.core.reserve,
                &a.core.fees,
                &a.core.room_vault,
                &a.core.room_mint,
                &user,
                &a.user_token,
                &tp,
                Some(&system),
                true,
                launch.first_buy_lamports,
                launch.min_tokens_out,
                now,
            )?;
        }
        door_check(
            &a.door,
            &di,
            &a.core.room,
            rk,
            &a.door_mint,
            &a.door_vault,
            &a.backing,
        )?;
        core_check(&a.core, a.door.accrued_sol)?;
        reserve_delta(before_l, before_r, &a.core)?;
        fee_delta(
            fl,
            a.core.fees.lamports(),
            fk,
            known(&a.core.room, &[&a.door]),
        )?;
        Ok(())
    }
    pub fn buy(ctx: Context<Trade>, lamports_in: u64, min_tokens_out: u64) -> Result<()> {
        trade(ctx, true, lamports_in, min_tokens_out)
    }
    pub fn sell(ctx: Context<Trade>, tokens_in: u64, min_lamports_out: u64) -> Result<()> {
        trade(ctx, false, tokens_in, min_lamports_out)
    }
    pub fn convert(ctx: Context<Convert>, amount: u64) -> Result<()> {
        let a = ctx.accounts;
        require!(!a.core.config.paused, Error::Paused);
        require!(amount > 0, Error::Amount);
        let ri = a.core.room.to_account_info();
        let rk = ri.key();
        let ai = a.door_a.to_account_info();
        let bi = a.door_b.to_account_info();
        require!(ai.key() != bi.key(), Error::Account);
        door_check(
            &a.door_a,
            &ai,
            &a.core.room,
            rk,
            &a.mint_a,
            &a.vault_a,
            &a.backing_a,
        )?;
        door_check(
            &a.door_b,
            &bi,
            &a.core.room,
            rk,
            &a.mint_b,
            &a.vault_b,
            &a.backing_b,
        )?;
        require!(
            amount <= a.door_a.backing && amount <= sub(U, a.door_b.backing)?,
            Error::Balance
        );
        user_ata(
            &a.user_a,
            &a.user.key(),
            a.mint_a.key,
            &spl_token_2022_interface::ID,
        )?;
        user_ata(
            &a.user_b,
            &a.user.key(),
            a.mint_b.key,
            &spl_token_2022_interface::ID,
        )?;
        let before_l = a.core.reserve.lamports();
        let before_r = a.core.room.reserve;
        let before_q = a.core.room.sold;
        let fl = a.core.fees.lamports();
        let fk = known(&a.core.room, &[&a.door_a, &a.door_b]);
        let ia = a.door_a.index.to_le_bytes();
        let ib = a.door_b.index.to_le_bytes();
        let ba = [a.door_a.bumps[0]];
        let bb = [a.door_b.bumps[0]];
        let sa: &[&[u8]] = &[b"door", rk.as_ref(), &ia, &ba];
        let sb: &[&[u8]] = &[b"door", rk.as_ref(), &ib, &bb];
        transfer(
            &a.user_a,
            &a.mint_a,
            &a.vault_a,
            &a.user,
            &a.token_program,
            amount,
            None,
            6,
        )?;
        transfer(
            &a.backing_a,
            &a.core.room_mint,
            &a.backing_b,
            &ai,
            &a.token_program,
            amount,
            Some(sa),
            6,
        )?;
        transfer(
            &a.vault_b,
            &a.mint_b,
            &a.user_b,
            &bi,
            &a.token_program,
            amount,
            Some(sb),
            6,
        )?;
        a.door_a.backing = sub(a.door_a.backing, amount)?;
        a.door_b.backing = add(a.door_b.backing, amount)?;
        let fee = a.core.config.convert_fee_lamports;
        deposit(&a.user, &a.core.fees, &a.system_program, fee)?;
        a.core.room.protocol_accrued_sol = add(a.core.room.protocol_accrued_sol, fee)?;
        door_check(
            &a.door_a,
            &ai,
            &a.core.room,
            rk,
            &a.mint_a,
            &a.vault_a,
            &a.backing_a,
        )?;
        door_check(
            &a.door_b,
            &bi,
            &a.core.room,
            rk,
            &a.mint_b,
            &a.vault_b,
            &a.backing_b,
        )?;
        require!(
            a.core.room.sold == before_q && a.core.room.reserve == before_r,
            Error::Invariant
        );
        core_check(&a.core, add(a.door_a.accrued_sol, a.door_b.accrued_sol)?)?;
        reserve_delta(before_l, before_r, &a.core)?;
        fee_delta(
            fl,
            a.core.fees.lamports(),
            fk,
            known(&a.core.room, &[&a.door_a, &a.door_b]),
        )?;
        emit!(Converted {
            room: rk,
            from: ai.key(),
            to: bi.key(),
            amount
        });
        Ok(())
    }
    pub fn retire_pending(ctx: Context<Retire>) -> Result<()> {
        let a = ctx.accounts;
        require!(!a.core.config.paused, Error::Paused);
        require!(a.core.room.status == 0, Error::PhaseTwo);
        let bl = a.core.reserve.lamports();
        let br = a.core.room.reserve;
        let fl = a.core.fees.lamports();
        let fk = known(&a.core.room, &[]);
        let r = &mut a.core.room;
        let n = r
            .pending_reserve_sol
            .min(sub(r.graduation_trigger_lamports, r.reserve)?);
        if n > 0 {
            let q = r.advance(n)?;
            let d = sub(q, r.sold)?;
            let rid = r.room_id.to_le_bytes();
            let rb = [r.bumps[0]];
            debit(&a.core.fees, &a.core.reserve, n)?;
            transfer(
                &a.core.room_vault,
                &a.core.room_mint,
                &a.retired_output,
                &r.to_account_info(),
                &a.token_program,
                d,
                Some(&[b"room", &rid, &rb]),
                6,
            )?;
            r.reserve = add(r.reserve, n)?;
            r.pending_reserve_sol = sub(r.pending_reserve_sol, n)?;
            r.sold = q;
            r.retired = add(r.retired, d)?;
            if r.reserve == r.graduation_trigger_lamports {
                r.status = 1;
            }
        }
        core_check(&a.core, 0)?;
        reserve_delta(bl, br, &a.core)?;
        fee_delta(fl, a.core.fees.lamports(), fk, known(&a.core.room, &[]))?;
        emit!(PendingRetired {
            room: a.core.room.key(),
            lamports: n,
            retired: a.core.room.retired
        });
        Ok(())
    }
    pub fn claim_door_fees(ctx: Context<Claim>) -> Result<()> {
        claim(ctx, 0)
    }
    pub fn claim_founder_fees(ctx: Context<Claim>) -> Result<()> {
        claim(ctx, 1)
    }
    pub fn sweep_protocol_fees(ctx: Context<Claim>) -> Result<()> {
        claim(ctx, 2)
    }
    pub fn set_fee_recipient(ctx: Context<SetRecipient>, new_recipient: Pubkey) -> Result<()> {
        let a = ctx.accounts;
        require_keys_eq!(a.authority.key(), a.door.fee_recipient, Error::Authority);
        require!(new_recipient != Pubkey::default(), Error::Authority);
        let bl = a.core.reserve.lamports();
        let br = a.core.room.reserve;
        let di = a.door.to_account_info();
        a.door.fee_recipient = new_recipient;
        door_check(
            &a.door,
            &di,
            &a.core.room,
            a.core.room.key(),
            &a.door_mint,
            &a.door_vault,
            &a.backing,
        )?;
        core_check(&a.core, a.door.accrued_sol)?;
        reserve_delta(bl, br, &a.core)?;
        emit!(FeeRecipientChanged {
            door: a.door.key(),
            recipient: new_recipient
        });
        Ok(())
    }
    pub fn release_slug(ctx: Context<ReleaseSlug>) -> Result<()> {
        require!(
            !ctx.accounts
                .room
                .live(&ctx.accounts.config, Clock::get()?.unix_timestamp)?,
            Error::Live
        );
        emit!(SlugReleased {
            identity: ctx.accounts.room.identity,
            room: ctx.accounts.room.key()
        });
        Ok(())
    }
}

#[allow(clippy::too_many_arguments)]
fn initialize_door<'a>(
    r: &mut Room,
    d: &mut Door,
    di: &AccountInfo<'a>,
    db: u8,
    rk: Pubkey,
    user: &AccountInfo<'a>,
    mint: &AccountInfo<'a>,
    vault: &AccountInfo<'a>,
    backing: &AccountInfo<'a>,
    room_mint: &AccountInfo<'a>,
    l: &Launch,
    system: &AccountInfo<'a>,
    tp: &AccountInfo<'a>,
    now: i64,
) -> Result<()> {
    let i = r.door_count;
    let ib = i.to_le_bytes();
    let bb = [db];
    let ds: &[&[u8]] = &[b"door", rk.as_ref(), &ib, &bb];
    let (mb, vb) = create_mint(
        user,
        mint,
        vault,
        di,
        rk,
        l,
        Some(i),
        system,
        tp,
        &[b"door_mint", rk.as_ref(), &ib],
        &[b"door_vault", di.key.as_ref()],
        ds,
    )?;
    let bk = create_token(
        user,
        backing,
        room_mint,
        di.key,
        system,
        tp,
        &[b"door_room_vault", di.key.as_ref()],
    )?;
    d.room = rk;
    d.index = i;
    d.mint = mint.key();
    d.door_vault = vault.key();
    d.room_token_vault = backing.key();
    d.creator = user.key();
    d.fee_recipient = user.key();
    d.bumps = [db, mb, vb, bk];
    d.created_at = now;
    d.matcher_version = l.matcher_version;
    d.rule = l.rule;
    d.face = l.face;
    r.door_count = r.door_count.checked_add(1).ok_or(Error::Overflow)?;
    emit!(DoorOpened {
        room: rk,
        door: di.key(),
        index: i,
        mint: mint.key(),
        matcher_version: l.matcher_version,
        rule: l.rule,
        face: l.face
    });
    Ok(())
}
fn require_top_level_launch() -> Result<()> {
    use anchor_lang::solana_program::instruction::{
        get_stack_height, TRANSACTION_LEVEL_STACK_HEIGHT,
    };
    require!(
        get_stack_height() == TRANSACTION_LEVEL_STACK_HEIGHT,
        Error::LaunchCpi
    );
    Ok(())
}
fn trade(ctx: Context<Trade>, buy: bool, amount: u64, min: u64) -> Result<()> {
    let a = ctx.accounts;
    require!(!a.core.config.paused, Error::Paused);
    let ri = a.core.room.to_account_info();
    let di = a.door.as_ref().map(|d| d.to_account_info());
    let route = if let Some(d) = a.door.as_mut() {
        Some(DoorRoute::new(
            d,
            di.as_ref().unwrap(),
            a.door_mint.as_ref().ok_or(Error::Account)?,
            a.door_vault.as_ref().ok_or(Error::Account)?,
            a.backing.as_ref().ok_or(Error::Account)?,
        ))
    } else {
        require!(
            a.door_mint.is_none() && a.door_vault.is_none() && a.backing.is_none(),
            Error::Account
        );
        None
    };
    execute_trade(
        &mut a.core.room,
        &ri,
        route,
        &a.core.reserve,
        &a.core.fees,
        &a.core.room_vault,
        &a.core.room_mint,
        &a.user,
        &a.user_token,
        &a.token_program,
        Some(&a.system_program),
        buy,
        amount,
        min,
        Clock::get()?.unix_timestamp,
    )?;
    core_check(&a.core, a.door.as_ref().map_or(0, |d| d.accrued_sol))?;
    Ok(())
}
fn claim(ctx: Context<Claim>, kind: u8) -> Result<()> {
    let a = ctx.accounts;
    let rk = a.core.room.key();
    let ri = a.core.room.to_account_info();
    let di = a.door.as_ref().map(|d| d.to_account_info());
    if let Some(d) = a.door.as_ref() {
        door_check(
            d,
            di.as_ref().unwrap(),
            &a.core.room,
            rk,
            a.door_mint.as_ref().ok_or(Error::Account)?,
            a.door_vault.as_ref().ok_or(Error::Account)?,
            a.backing.as_ref().ok_or(Error::Account)?,
        )?;
    } else {
        require!(
            a.door_mint.is_none() && a.door_vault.is_none() && a.backing.is_none(),
            Error::Account
        );
    }
    let recipient = match kind {
        0 => a.door.as_ref().ok_or(Error::Account)?.fee_recipient,
        1 => a.core.room.founder,
        _ => a.core.config.protocol_fee_recipient,
    };
    require_keys_eq!(a.recipient.key(), recipient, Error::Authority);
    if kind < 2 {
        require_keys_eq!(a.authority.key(), recipient, Error::Authority);
    }
    if kind != 0 {
        require!(a.door.is_none(), Error::Account);
    }
    user_ata(
        &a.recipient_wsol,
        &recipient,
        &spl_token_interface::native_mint::ID,
        &spl_token_interface::ID,
    )?;
    token(
        &a.fee_wsol,
        &spl_token_interface::native_mint::ID,
        &rk,
        &spl_token_interface::ID,
    )?;
    let (sol, wsol) = match kind {
        0 => {
            let d = a.door.as_ref().unwrap();
            (d.accrued_sol, d.accrued_wsol)
        }
        1 => (
            a.core.room.founder_accrued,
            a.core.room.founder_accrued_wsol,
        ),
        _ => (
            a.core.room.protocol_accrued_sol,
            a.core.room.protocol_accrued_wsol,
        ),
    };
    let bl = a.core.reserve.lamports();
    let br = a.core.room.reserve;
    let fl = a.core.fees.lamports();
    let fk = known(
        &a.core.room,
        &a.door.as_ref().map(|d| vec![&***d]).unwrap_or_default(),
    );
    let fw = amount(&a.fee_wsol)?;
    let known_w = a.core.room.founder_accrued_wsol as u128
        + a.core.room.protocol_accrued_wsol as u128
        + a.core.room.pending_reserve_wsol as u128
        + a.door.as_ref().map_or(0, |d| d.accrued_wsol) as u128;
    require!(fw as u128 >= known_w, Error::Invariant);
    if sol > 0 {
        debit(&a.core.fees, &a.recipient, sol)?;
    }
    if wsol > 0 {
        let rid = a.core.room.room_id.to_le_bytes();
        let b = [a.core.room.bumps[0]];
        transfer(
            &a.fee_wsol,
            &a.wsol_mint,
            &a.recipient_wsol,
            &ri,
            &a.classic_token_program,
            wsol,
            Some(&[b"room", &rid, &b]),
            9,
        )?;
    }
    match kind {
        0 => {
            let d = a.door.as_mut().unwrap();
            d.accrued_sol = 0;
            d.accrued_wsol = 0;
            d.claimed_sol = add(d.claimed_sol, sol)?;
            d.claimed_wsol = add(d.claimed_wsol, wsol)?;
        }
        1 => {
            a.core.room.founder_accrued = 0;
            a.core.room.founder_accrued_wsol = 0;
        }
        _ => {
            a.core.room.protocol_accrued_sol = 0;
            a.core.room.protocol_accrued_wsol = 0;
        }
    }
    require!(amount(&a.fee_wsol)? == sub(fw, wsol)?, Error::Invariant);
    core_check(&a.core, a.door.as_ref().map_or(0, |d| d.accrued_sol))?;
    reserve_delta(bl, br, &a.core)?;
    fee_delta(
        fl,
        a.core.fees.lamports(),
        fk,
        known(
            &a.core.room,
            &a.door.as_ref().map(|d| vec![&***d]).unwrap_or_default(),
        ),
    )?;
    if let Some(d) = a.door.as_ref() {
        door_check(
            d,
            di.as_ref().unwrap(),
            &a.core.room,
            rk,
            a.door_mint.as_ref().unwrap(),
            a.door_vault.as_ref().unwrap(),
            a.backing.as_ref().unwrap(),
        )?;
    }
    if kind == 1 {
        emit!(FounderFeesClaimed {
            room: rk,
            founder: recipient,
            sol,
            wsol
        });
    } else {
        emit!(FeesClaimed {
            room: rk,
            recipient,
            kind,
            sol,
            wsol
        });
    }
    Ok(())
}

#[event]
pub struct ConfigChanged {
    pub admin: Pubkey,
    pub matcher: Pubkey,
    pub founder_share_bps: u16,
    pub settings: Settings,
}
#[event]
pub struct RoomCreated {
    pub room: Pubkey,
    pub room_id: u64,
    pub identity: [u8; 32],
    pub founder: Pubkey,
    pub founder_share_bps: u16,
    pub matcher_version: u16,
    pub rule: u8,
    pub face: u32,
}
#[event]
pub struct DoorOpened {
    pub room: Pubkey,
    pub door: Pubkey,
    pub index: u32,
    pub mint: Pubkey,
    pub matcher_version: u16,
    pub rule: u8,
    pub face: u32,
}
#[event]
pub struct TradeEvent {
    pub room: Pubkey,
    pub door: Option<Pubkey>,
    pub user: Pubkey,
    pub buy: bool,
    pub tokens: u64,
    pub curve_lamports: u64,
    pub fee: u64,
    pub sold: u64,
    pub reserve: u64,
    pub status: u8,
}
#[event]
pub struct Converted {
    pub room: Pubkey,
    pub from: Pubkey,
    pub to: Pubkey,
    pub amount: u64,
}
#[event]
pub struct PendingRetired {
    pub room: Pubkey,
    pub lamports: u64,
    pub retired: u64,
}
#[event]
pub struct FeesClaimed {
    pub room: Pubkey,
    pub recipient: Pubkey,
    pub kind: u8,
    pub sol: u64,
    pub wsol: u64,
}
#[event]
pub struct FounderFeesClaimed {
    pub room: Pubkey,
    pub founder: Pubkey,
    pub sol: u64,
    pub wsol: u64,
}
#[event]
pub struct FeeRecipientChanged {
    pub door: Pubkey,
    pub recipient: Pubkey,
}
#[event]
pub struct SlugReleased {
    pub identity: [u8; 32],
    pub room: Pubkey,
}

#[error_code]
pub enum Error {
    #[msg("Checked arithmetic overflow")]
    Overflow,
    #[msg("Insufficient accounted inventory or balance")]
    Balance,
    #[msg("Invalid config or share bounds")]
    BadConfig,
    #[msg("Invalid metadata or evidence")]
    Metadata,
    #[msg("Invalid account identity, owner or mint")]
    Account,
    #[msg("Invalid PDA")]
    Pda,
    #[msg("Unauthorized")]
    Authority,
    #[msg("Matcher must co-sign the whole transaction")]
    Matcher,
    #[msg("Instruction invariant failed")]
    Invariant,
    #[msg("Program paused")]
    Paused,
    #[msg("Room is not live")]
    Dead,
    #[msg("Identity holder is live")]
    Live,
    #[msg("Invalid identity lock")]
    Identity,
    #[msg("Identity holder is required and must match lock")]
    Holder,
    #[msg("Phase 2 is not implemented or curve is complete")]
    PhaseTwo,
    #[msg("Invalid zero amount")]
    Amount,
    #[msg("Slippage limit exceeded")]
    Slippage,
    #[msg("Invalid execution clock")]
    Clock,
    #[msg("Launch routing and metadata must be a top-level co-signed instruction")]
    LaunchCpi,
}
