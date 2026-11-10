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

declare_id!("8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ");

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
        // The liveness gate changes only through propose_gate + apply_gate, after GATE_DELAY_SECONDS.
        require!(settings.gate() == c.gate(), Error::GateTimelock);
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
    pub fn propose_gate(ctx: Context<ProposeGate>, gate: Gate) -> Result<()> {
        let a = ctx.accounts;
        let now = Clock::get()?.unix_timestamp;
        let bump = if a.pending.data_is_empty() {
            create_pda(
                &a.admin.to_account_info(),
                &a.pending,
                &a.system_program.to_account_info(),
                &crate::ID,
                PendingGate::LEN,
                PendingGate::LEN,
                &[b"gate"],
            )?
        } else {
            require_keys_eq!(*a.pending.owner, crate::ID, Error::Account);
            PendingGate::try_deserialize(&mut &a.pending.try_borrow_data()?[..])?;
            pda(&a.pending, &[b"gate"])?
        };
        let effective_at = now.checked_add(GATE_DELAY_SECONDS).ok_or(Error::Overflow)?;
        PendingGate {
            gate,
            proposed_at: now,
            effective_at,
            bump,
        }
        .try_serialize(&mut &mut a.pending.try_borrow_mut_data()?[..])?;
        emit!(GateChangeProposed {
            current: a.config.gate(),
            proposed: gate,
            proposed_at: now,
            effective_at,
        });
        Ok(())
    }
    /// Permissionless once the delay has passed: the change is already public and committed.
    pub fn apply_gate(ctx: Context<ApplyGate>) -> Result<()> {
        let now = Clock::get()?.unix_timestamp;
        let p = &ctx.accounts.pending;
        require!(now >= p.effective_at, Error::GateTimelock);
        let gate = p.gate;
        let c = &mut ctx.accounts.config;
        c.set_gate(gate);
        emit!(ConfigChanged {
            admin: c.admin,
            matcher: c.matcher_authority,
            founder_share_bps: c.founder_share_bps,
            settings: c.settings(),
        });
        emit!(GateChangeApplied {
            gate,
            applied_at: now
        });
        Ok(())
    }
    pub fn cancel_gate(ctx: Context<CancelGate>) -> Result<()> {
        emit!(GateChangeCancelled {
            cancelled: ctx.accounts.pending.gate,
            cancelled_at: Clock::get()?.unix_timestamp,
        });
        Ok(())
    }
    // Separate the compact reserve wire format from previously signed price-bound launches.
    #[instruction(discriminator = [229, 160, 197, 44, 79, 28, 117, 166])]
    pub fn create_room(
        ctx: Context<CreateRoom>,
        room_id: u64,
        launch: Launch,
        name_key: Option<[u8; NAME_KEY_LEN]>,
    ) -> Result<()> {
        require_top_level_launch()?;
        let a = ctx.accounts;
        launch.validate()?;
        require!(launch.door_nonce == 0, Error::DoorNonce);
        launch_window(&launch)?;
        require!(!a.config.paused, Error::Paused);
        let fee = add(a.config.room_fee_lamports, a.config.door_fee_lamports)?;
        require!(fee <= launch.max_fee_lamports, Error::FeeLimit);
        require!(
            launch.expected_terms_hash == a.config.launch_terms_hash(),
            Error::LaunchTerms
        );
        let now = Clock::get()?.unix_timestamp;
        // Validate exact-identity floor before any persistent side effect (all CPIs atomic).
        let identity = launch.identity();
        let old = read_slug(&a.slug, &identity)?;
        if let Some(lock) = &old {
            holder_dead(lock.room_id, a.old_holder.as_deref(), &a.config, now)?;
        } else {
            require!(a.old_holder.is_none(), Error::Holder);
        }
        // Matcher-keyed name floor (H-1): the key is the matcher's, uniqueness is the program's.
        let name_old = match (&name_key, a.name_lock.as_ref()) {
            (None, None) => {
                require!(a.old_name_holder.is_none(), Error::Holder);
                None
            }
            (Some(key), Some(lock)) => {
                let old = read_name(lock, key)?;
                if let Some(held) = &old {
                    holder_dead(held.room_id, a.old_name_holder.as_deref(), &a.config, now)?;
                } else {
                    require!(a.old_name_holder.is_none(), Error::Holder);
                }
                Some(old.is_some())
            }
            _ => return err!(Error::NameLock),
        };
        let room_info = a.room.to_account_info();
        let rk = a.room.key();
        let rid = room_id.to_le_bytes();
        let rb = [ctx.bumps.room];
        let rs: &[&[u8]] = &[b"room", &rid, &rb];
        let user = a.user.to_account_info();
        let system = a.system_program.to_account_info();
        let tp = a.token_program.to_account_info();
        let reserve_b = empty_pda(&a.reserve, &[b"reserve", rk.as_ref()])?;
        let fee_b = empty_pda(&a.fees, &[b"fees", rk.as_ref()])?;
        let grad_b = empty_pda(&a.grad_payer, &[b"grad_payer", rk.as_ref()])?;
        if launch.first_buy_lamports > 0 {
            ensure_native(&user, &a.reserve, &system, &[b"reserve", rk.as_ref()])?;
        }
        if fee > 0 || launch.first_buy_lamports > 0 {
            ensure_native(&user, &a.fees, &system, &[b"fees", rk.as_ref()])?;
        }
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
        let retired_b = empty_pda(&a.retired, &[b"retired", rk.as_ref()])?;
        let fw_b = empty_pda(&a.fee_wsol, &[b"fee_wsol", rk.as_ref()])?;
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
        if let (Some(key), Some(lock), Some(taken)) = (&name_key, a.name_lock.as_ref(), name_old) {
            let bump = if taken {
                pda(lock, &[b"name", key])?
            } else {
                create_pda(
                    &user,
                    lock,
                    &system,
                    &crate::ID,
                    NameLock::LEN,
                    NameLock::LEN,
                    &[b"name", key],
                )?
            };
            NameLock {
                room_id,
                key: *key,
                bump,
            }
            .try_serialize(&mut &mut lock.try_borrow_mut_data()?[..])?;
        }
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
        launch.check_room_reserve(r.reserve)?;
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
            face: launch.face,
            name_key
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
                &a.retired,
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
    #[instruction(discriminator = [164, 83, 47, 138, 236, 0, 239, 227])]
    pub fn open_door(ctx: Context<OpenDoor>, launch: Launch) -> Result<()> {
        require_top_level_launch()?;
        let a = ctx.accounts;
        launch.validate()?;
        require!(launch.door_nonce != 0, Error::DoorNonce);
        launch_window(&launch)?;
        let now = Clock::get()?.unix_timestamp;
        require!(!a.core.config.paused, Error::Paused);
        let fee = a.core.config.door_fee_lamports;
        require!(fee <= launch.max_fee_lamports, Error::FeeLimit);
        require!(a.core.room.live(&a.core.config, now)?, Error::Dead);
        launch.check_room_reserve(a.core.room.reserve)?;
        let identity = launch.identity();
        if let Some(lock) = read_slug(&a.slug, &identity)? {
            if lock.room_id != a.core.room.room_id {
                holder_dead(lock.room_id, a.old_holder.as_deref(), &a.core.config, now)?;
            } else {
                require!(a.old_holder.is_none(), Error::Holder);
            }
        } else {
            require!(a.old_holder.is_none(), Error::Holder);
        }
        if launch.first_buy_lamports > 0 {
            ensure_native(
                &a.user.to_account_info(),
                &a.core.reserve,
                &a.system_program.to_account_info(),
                &[b"reserve", a.core.room.key().as_ref()],
            )?;
        }
        if fee > 0 || launch.first_buy_lamports > 0 {
            ensure_native(
                &a.user.to_account_info(),
                &a.core.fees,
                &a.system_program.to_account_info(),
                &[b"fees", a.core.room.key().as_ref()],
            )?;
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
                &a.core.retired,
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
    pub fn buy(ctx: Context<TradeAccounts>, lamports_in: u64, min_tokens_out: u64) -> Result<()> {
        trade(ctx, true, lamports_in, min_tokens_out)
    }
    pub fn sell(ctx: Context<TradeAccounts>, tokens_in: u64, min_lamports_out: u64) -> Result<()> {
        trade(ctx, false, tokens_in, min_lamports_out)
    }
    pub fn buy_door(
        ctx: Context<TradeAccounts>,
        lamports_in: u64,
        min_door_tokens_out: u64,
    ) -> Result<()> {
        require!(ctx.accounts.door.is_some(), Error::Account);
        trade(ctx, true, lamports_in, min_door_tokens_out)
    }
    pub fn sell_door(
        ctx: Context<TradeAccounts>,
        door_tokens_in: u64,
        min_lamports_out: u64,
    ) -> Result<()> {
        require!(ctx.accounts.door.is_some(), Error::Account);
        trade(ctx, false, door_tokens_in, min_lamports_out)
    }
    pub fn swap_doors(ctx: Context<SwapDoors>, door_tokens_in: u64, min_out: u64) -> Result<()> {
        let a = ctx.accounts;
        // Like the prior same-room conversion, a swap has no room SOL leg.
        require!(door_tokens_in > 0, Error::Amount);
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
        let next_a = sub(a.door_a.sold, door_tokens_in)?;
        let room_tokens = sub(
            door_integral(a.door_a.virtual_quote, a.door_a.sold)?,
            door_integral(a.door_a.virtual_quote, next_a)?,
        )?;
        let fee = ratio(room_tokens, SWAP_FEE_BPS, true)?;
        let net = sub(room_tokens, fee)?;
        require!(net > 0 && room_tokens <= a.door_a.backing, Error::Amount);
        let next_b = door_advance(a.door_b.virtual_quote, a.door_b.sold, net)?;
        let door_tokens_out = sub(next_b, a.door_b.sold)?;
        require!(
            door_tokens_out > 0 && door_tokens_out >= min_out,
            Error::Slippage
        );
        pda(&a.swap_fees, &[b"swap_fees", rk.as_ref()])?;
        let quote_mint = a.core.room.room_mint;
        if a.swap_fees.data_is_empty() {
            create_token(
                &a.user,
                &a.swap_fees,
                &a.core.room_mint,
                &rk,
                &a.system_program,
                &a.token_program,
                &[b"swap_fees", rk.as_ref()],
            )?;
        }
        if a.backing_b.data_is_empty() {
            create_token(
                &a.user,
                &a.backing_b,
                &a.core.room_mint,
                &bi.key(),
                &a.system_program,
                &a.token_program,
                &[b"door_room_vault", bi.key.as_ref()],
            )?;
        }
        let fee_before = token(&a.swap_fees, &quote_mint, &rk, a.token_program.key)?;
        let known_before = a.core.room.swap_fees_unclaimed;
        require!(fee_before >= known_before, Error::Invariant);
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
        let ia = a.door_a.nonce.to_le_bytes();
        let ib = a.door_b.nonce.to_le_bytes();
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
            door_tokens_in,
            None,
            6,
        )?;
        transfer(
            &a.backing_a,
            &a.core.room_mint,
            &a.backing_b,
            &ai,
            &a.token_program,
            net,
            Some(sa),
            6,
        )?;
        transfer(
            &a.backing_a,
            &a.core.room_mint,
            &a.swap_fees,
            &ai,
            &a.token_program,
            fee,
            Some(sa),
            6,
        )?;
        transfer(
            &a.vault_b,
            &a.mint_b,
            &a.user_b,
            &bi,
            &a.token_program,
            door_tokens_out,
            Some(sb),
            6,
        )?;
        a.door_a.sold = next_a;
        a.door_b.sold = next_b;
        a.door_a.backing = sub(a.door_a.backing, room_tokens)?;
        a.door_b.backing = add(a.door_b.backing, net)?;
        let door_fee = ratio(fee, SWAP_DOOR_SHARE_BPS, false)?;
        a.door_b.accrued_room = add(a.door_b.accrued_room, door_fee)?;
        a.core.room.protocol_accrued_room =
            add(a.core.room.protocol_accrued_room, sub(fee, door_fee)?)?;
        a.core.room.swap_fees_unclaimed = add(known_before, fee)?;
        let known_after = a.core.room.swap_fees_unclaimed;
        let fee_after = token(&a.swap_fees, &quote_mint, &rk, a.token_program.key)?;
        require!(
            sub(fee_after, fee_before)? == fee
                && sub(known_after, known_before)? == fee
                && fee_after >= known_after,
            Error::Invariant
        );
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
        emit!(DoorsSwapped {
            room: rk,
            from: ai.key(),
            to: bi.key(),
            door_tokens_in,
            door_tokens_out,
            room_tokens,
            fee,
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
        let ri = a.core.room.to_account_info();
        if a.core.room.pending_reserve_sol > 0 && a.retired_output.data_is_empty() {
            create_token(
                &a.payer,
                &a.retired_output,
                &a.core.room_mint,
                &ri.key(),
                &a.system_program,
                &a.token_program,
                &[b"retired", ri.key.as_ref()],
            )?;
        }
        let settled = settle_pending(
            &mut a.core.room,
            &ri,
            &a.core.room_vault,
            &a.core.room_mint,
            &a.retired_output,
            &a.token_program,
        )?;
        if settled > 0 {
            debit(&a.core.fees, &a.core.reserve, settled)?;
        }
        core_check(&a.core, 0)?;
        reserve_delta(bl, br, &a.core)?;
        fee_delta(fl, a.core.fees.lamports(), fk, known(&a.core.room, &[]))?;
        Ok(())
    }
    pub fn claim_door_swap_fees(ctx: Context<ClaimSwapFees>) -> Result<()> {
        claim_swap_fees(ctx, true)
    }
    pub fn claim_protocol_swap_fees(ctx: Context<ClaimSwapFees>) -> Result<()> {
        claim_swap_fees(ctx, false)
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
    /// Permissionless, like release_slug and under the same rule: a NameLock whose room is not live
    /// is closed and its rent paid to the caller.
    pub fn release_name(ctx: Context<ReleaseName>) -> Result<()> {
        require!(
            !ctx.accounts
                .room
                .live(&ctx.accounts.config, Clock::get()?.unix_timestamp)?,
            Error::Live
        );
        emit!(NameReleased {
            key: ctx.accounts.name_lock.key,
            room: ctx.accounts.room.key()
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
    // The address comes from the signed nonce; `index` is a creation-order statistic.
    let i = r.door_count;
    let nb = l.door_nonce.to_le_bytes();
    let bb = [db];
    let ds: &[&[u8]] = &[b"door", rk.as_ref(), &nb, &bb];
    let (mb, vb) = create_mint(
        user,
        mint,
        vault,
        di,
        rk,
        l,
        Some((i, l.door_nonce)),
        system,
        tp,
        &[b"door_mint", rk.as_ref(), &nb],
        &[b"door_vault", di.key.as_ref()],
        ds,
    )?;
    let bk = empty_pda(backing, &[b"door_room_vault", di.key.as_ref()])?;
    d.room = rk;
    d.index = i;
    d.mint = mint.key();
    d.door_vault = vault.key();
    d.room_token_vault = backing.key();
    let room_price = r.price()?;
    d.virtual_quote = door_virtual_quote(room_price.numerator, room_price.denominator)?;
    d.creator = user.key();
    d.fee_recipient = user.key();
    d.bumps = [db, mb, vb, bk];
    d.created_at = now;
    d.matcher_version = l.matcher_version;
    d.rule = l.rule;
    d.face = l.face;
    d.nonce = l.door_nonce;
    r.door_count = r.door_count.checked_add(1).ok_or(Error::Overflow)?;
    emit!(DoorOpened {
        room: rk,
        door: di.key(),
        index: i,
        mint: mint.key(),
        matcher_version: l.matcher_version,
        rule: l.rule,
        face: l.face,
        nonce: l.door_nonce
    });
    Ok(())
}
/// A signed launch executes only at or before `expires_at_slot`, and never more than
/// `MAX_LAUNCH_WINDOW_SLOTS` ahead of the executing slot: the same bound the runtime puts
/// on a recent blockhash (MAX_PROCESSING_AGE = 150), but independent of how the
/// transaction is built, so a durable-nonce transaction cannot outlive it.
fn launch_window(l: &Launch) -> Result<()> {
    let slot = Clock::get()?.slot;
    require!(
        slot <= l.expires_at_slot && l.expires_at_slot - slot <= MAX_LAUNCH_WINDOW_SLOTS,
        Error::Expired
    );
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
fn trade(ctx: Context<TradeAccounts>, buy: bool, amount: u64, min: u64) -> Result<()> {
    let a = ctx.accounts;
    // Pause stops new positions only. Sells stay open so a holder can always exit at the
    // curve price; every sell invariant is asserted per instruction and needs no buy.
    require!(!buy || !a.core.config.paused, Error::Paused);
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
        &a.core.retired,
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
fn claim_swap_fees(ctx: Context<ClaimSwapFees>, door_claim: bool) -> Result<()> {
    let a = ctx.accounts;
    let rk = a.core.room.key();
    let ri = a.core.room.to_account_info();
    let recipient = if door_claim {
        let door = a.door.as_ref().ok_or(Error::Account)?;
        door_check(
            door,
            &door.to_account_info(),
            &a.core.room,
            rk,
            a.door_mint.as_ref().ok_or(Error::Account)?,
            a.door_vault.as_ref().ok_or(Error::Account)?,
            a.backing.as_ref().ok_or(Error::Account)?,
        )?;
        door.fee_recipient
    } else {
        require!(
            a.door.is_none()
                && a.door_mint.is_none()
                && a.door_vault.is_none()
                && a.backing.is_none(),
            Error::Account
        );
        a.core.config.protocol_fee_recipient
    };
    require_keys_eq!(a.authority.key(), recipient, Error::Authority);
    user_ata(
        &a.recipient_token,
        &recipient,
        &a.core.room.room_mint,
        a.token_program.key,
    )?;
    pda(&a.swap_fees, &[b"swap_fees", rk.as_ref()])?;
    let before = token(
        &a.swap_fees,
        &a.core.room.room_mint,
        &rk,
        a.token_program.key,
    )?;
    let unclaimed = a.core.room.swap_fees_unclaimed;
    require!(before >= unclaimed, Error::Invariant);
    let amount = if door_claim {
        a.door.as_ref().unwrap().accrued_room
    } else {
        a.core.room.protocol_accrued_room
    };
    let remaining = sub(unclaimed, amount)?;
    let reserve_lamports = a.core.reserve.lamports();
    let reserve = a.core.room.reserve;
    let sold = a.core.room.sold;
    if amount > 0 {
        let rid = a.core.room.room_id.to_le_bytes();
        let bump = [a.core.room.bumps[0]];
        transfer(
            &a.swap_fees,
            &a.core.room_mint,
            &a.recipient_token,
            &ri,
            &a.token_program,
            amount,
            Some(&[b"room", &rid, &bump]),
            6,
        )?;
    }
    if door_claim {
        a.door.as_mut().unwrap().accrued_room = 0;
    } else {
        a.core.room.protocol_accrued_room = 0;
    }
    a.core.room.swap_fees_unclaimed = remaining;
    let after = token(
        &a.swap_fees,
        &a.core.room.room_mint,
        &rk,
        a.token_program.key,
    )?;
    require!(
        after == sub(before, amount)? && after >= remaining,
        Error::Invariant
    );
    require!(
        a.core.room.sold == sold && a.core.room.reserve == reserve,
        Error::Invariant
    );
    core_check(&a.core, a.door.as_ref().map_or(0, |door| door.accrued_sol))?;
    reserve_delta(reserve_lamports, reserve, &a.core)?;
    emit!(SwapFeesClaimed {
        room: rk,
        door: a.door.as_ref().map(|door| door.key()),
        recipient,
        room_tokens: amount,
    });
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
    if a.fee_wsol.data_is_empty() {
        create_token(
            &a.authority,
            &a.fee_wsol,
            &a.wsol_mint,
            &rk,
            &a.system_program,
            &a.classic_token_program,
            &[b"fee_wsol", rk.as_ref()],
        )?;
    }
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
    // Direct lamport edits only after the instruction's last CPI: the runtime syncs only
    // CPI-passed accounts, so an edit followed by a CPI that passes one of the two edited
    // accounts fails as UnbalancedInstruction (the class that broke 8ce373f).
    if sol > 0 {
        debit(&a.core.fees, &a.recipient, sol)?;
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
pub struct SwapFeesClaimed {
    pub room: Pubkey,
    pub door: Option<Pubkey>,
    pub recipient: Pubkey,
    pub room_tokens: u64,
}

#[event]
pub struct ConfigChanged {
    pub admin: Pubkey,
    pub matcher: Pubkey,
    pub founder_share_bps: u16,
    pub settings: Settings,
}
#[event]
pub struct GateChangeProposed {
    pub current: Gate,
    pub proposed: Gate,
    pub proposed_at: i64,
    pub effective_at: i64,
}
#[event]
pub struct GateChangeApplied {
    pub gate: Gate,
    pub applied_at: i64,
}
#[event]
pub struct GateChangeCancelled {
    pub cancelled: Gate,
    pub cancelled_at: i64,
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
    pub name_key: Option<[u8; NAME_KEY_LEN]>,
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
    pub nonce: u64,
}
#[event]
pub struct Trade {
    pub room: Pubkey,
    pub door: Option<Pubkey>,
    pub user: Pubkey,
    pub buy: bool,
    pub tokens: u64,
    pub room_tokens: u64,
    pub curve_lamports: u64,
    pub fee: u64,
    pub sold_after: u64,
    pub reserve: u64,
    pub status: u8,
    pub price_after: Price,
}
#[event]
pub struct DoorsSwapped {
    pub room: Pubkey,
    pub from: Pubkey,
    pub to: Pubkey,
    pub door_tokens_in: u64,
    pub door_tokens_out: u64,
    pub room_tokens: u64,
    pub fee: u64,
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
#[event]
pub struct NameReleased {
    pub key: [u8; NAME_KEY_LEN],
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
    #[msg("Phase 2 is not implemented or the buy cap has been reached")]
    PhaseTwo,
    #[msg("Invalid zero amount")]
    Amount,
    #[msg("Slippage limit exceeded")]
    Slippage,
    #[msg("Invalid execution clock")]
    Clock,
    #[msg("Launch routing and metadata must be a top-level co-signed instruction")]
    LaunchCpi,
    #[msg("Flat protocol fee exceeds the signed maximum")]
    FeeLimit,
    #[msg("Room economics differ from the signed launch terms")]
    LaunchTerms,
    #[msg("Signed launch is past its expiry slot, or its expiry is too far ahead")]
    Expired,
    #[msg("Door nonce must be 0 for create_room and non-zero for open_door")]
    DoorNonce,
    #[msg(
        "Liveness-gate changes take effect only through propose_gate + apply_gate, after the delay"
    )]
    GateTimelock,
    #[msg("name_key and the name_lock account must be given together")]
    NameLock,
    #[msg("Door buy exceeds the unsold door supply")]
    DoorSupplyExhausted,
}
