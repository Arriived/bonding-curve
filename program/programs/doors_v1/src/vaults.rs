//! Raw token amounts are used ONLY for validation and exact delta assertions.
//! Pricing, inventory, payouts, retirement and claims use state counters.
use crate::{contexts::Core, math::*, state::*, Error};
use anchor_lang::solana_program::program_pack::IsInitialized;
use anchor_lang::{
    prelude::*,
    solana_program::{
        program::{invoke, invoke_signed},
        program_option::COption,
        system_instruction,
    },
};
use spl_token_2022_interface::{
    extension::{metadata_pointer::MetadataPointer, BaseStateWithExtensions, StateWithExtensions},
    state::{Account as TokenAccount, Mint},
};
use spl_token_metadata_interface::{
    instruction as meta,
    state::{Field, TokenMetadata},
};

pub const ATA: Pubkey = anchor_lang::pubkey!("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL");
pub fn pda(ai: &AccountInfo, seeds: &[&[u8]]) -> Result<u8> {
    let (key, bump) = Pubkey::find_program_address(seeds, &crate::ID);
    require_keys_eq!(ai.key(), key, Error::Pda);
    Ok(bump)
}
pub fn deposit<'a>(
    user: &AccountInfo<'a>,
    to: &AccountInfo<'a>,
    system: &AccountInfo<'a>,
    n: u64,
) -> Result<()> {
    if n > 0 {
        let before = to.lamports();
        invoke(
            &system_instruction::transfer(user.key, to.key, n),
            &[user.clone(), to.clone(), system.clone()],
        )?;
        require!(to.lamports() == add(before, n)?, Error::Invariant);
    }
    Ok(())
}
pub fn debit(from: &AccountInfo, to: &AccountInfo, n: u64) -> Result<()> {
    require_keys_eq!(*from.owner, crate::ID, Error::Authority);
    require!(from.key != to.key, Error::Account);
    let before = from.lamports();
    let dest = to.lamports();
    **from.try_borrow_mut_lamports()? = sub(before, n)?;
    **to.try_borrow_mut_lamports()? = add(dest, n)?;
    require!(
        before - from.lamports() == n && to.lamports() - dest == n,
        Error::Invariant
    );
    Ok(())
}
pub fn create_pda<'a>(
    user: &AccountInfo<'a>,
    target: &AccountInfo<'a>,
    system: &AccountInfo<'a>,
    owner: &Pubkey,
    space: usize,
    funded_space: usize,
    seeds: &[&[u8]],
) -> Result<u8> {
    let bump = pda(target, seeds)?;
    require_keys_eq!(
        *target.owner,
        anchor_lang::system_program::ID,
        Error::Account
    );
    require!(target.data_is_empty(), Error::Account);
    let mut signed = seeds.to_vec();
    let bb = [bump];
    signed.push(&bb);
    let rent = Rent::get()?.minimum_balance(funded_space);
    if target.lamports() == 0 {
        // A fresh account needs one System CPI. Always using transfer +
        // allocate + assign would overflow the transaction instruction trace
        // when creating both mints and executing the optional first buy.
        invoke_signed(
            &system_instruction::create_account(user.key, target.key, rent, space as u64, owner),
            &[user.clone(), target.clone(), system.clone()],
            &[&signed],
        )?;
        return Ok(bump);
    }
    // Prefunded by someone else (anyone can send lamports to a PDA). One CPI tops up, allocates and
    // assigns: SIMD-0312 CreateAccountAllowPrefund, active on devnet (slot 454,464,000) and mainnet
    // (slot 422,928,004). The former transfer + allocate + assign cost three trace entries per account,
    // which let a third party push a launch to the 64-entry instruction-trace limit (finding M-8).
    let needed = rent.saturating_sub(target.lamports());
    if needed == 0 && space == 0 && owner == &anchor_lang::system_program::ID {
        return Ok(bump); // a funded, empty, system-owned PDA is already what was asked for
    }
    let before = target.lamports();
    invoke_signed(
        &allow_prefund_ix(
            target.key,
            (needed > 0).then_some((user.key, needed)),
            space as u64,
            owner,
        ),
        &[target.clone(), user.clone(), system.clone()],
        &[&signed],
    )?;
    require!(
        target.lamports() == add(before, needed)?
            && target.data_len() == space
            && target.owner == owner,
        Error::Invariant
    );
    Ok(bump)
}
/// `SystemInstruction::CreateAccountAllowPrefund` built with exact-size allocations. The library
/// builder pushes the payer onto a one-element `Vec`, which on the never-freed SBF heap strands the first
/// buffer and over-allocates the second; across a launch's account creations that cost more heap than
/// the three CPIs it replaces. Byte-identical to
/// `system_instruction::create_account_allow_prefund` (asserted by the SBF suite).
pub fn allow_prefund_ix(
    target: &Pubkey,
    payer_and_lamports: Option<(&Pubkey, u64)>,
    space: u64,
    owner: &Pubkey,
) -> anchor_lang::solana_program::instruction::Instruction {
    use anchor_lang::solana_program::instruction::{AccountMeta, Instruction};
    const CREATE_ACCOUNT_ALLOW_PREFUND: u32 = 13; // SystemInstruction variant index
    let mut accounts = Vec::with_capacity(1 + payer_and_lamports.is_some() as usize);
    accounts.push(AccountMeta::new(*target, true));
    let lamports = payer_and_lamports.map_or(0, |(payer, lamports)| {
        accounts.push(AccountMeta::new(*payer, true));
        lamports
    });
    let mut data = Vec::with_capacity(52);
    data.extend_from_slice(&CREATE_ACCOUNT_ALLOW_PREFUND.to_le_bytes());
    data.extend_from_slice(&lamports.to_le_bytes());
    data.extend_from_slice(&space.to_le_bytes());
    data.extend_from_slice(owner.as_ref());
    Instruction {
        program_id: anchor_lang::system_program::ID,
        accounts,
        data,
    }
}
pub fn token(ai: &AccountInfo, mint: &Pubkey, owner: &Pubkey, program: &Pubkey) -> Result<u64> {
    require_keys_eq!(*ai.owner, *program, Error::Account);
    let data = ai.try_borrow_data()?;
    let a = StateWithExtensions::<TokenAccount>::unpack(&data)?;
    require_keys_eq!(a.base.mint, *mint, Error::Account);
    require_keys_eq!(a.base.owner, *owner, Error::Authority);
    require!(
        a.base.is_initialized() && !a.base.is_frozen(),
        Error::Account
    );
    Ok(a.base.amount)
}
pub fn amount(ai: &AccountInfo) -> Result<u64> {
    require!(
        ai.owner == &spl_token_2022_interface::ID || ai.owner == &spl_token_interface::ID,
        Error::Account
    );
    Ok(
        StateWithExtensions::<TokenAccount>::unpack(&ai.try_borrow_data()?)?
            .base
            .amount,
    )
}
pub fn user_ata(ai: &AccountInfo, user: &Pubkey, mint: &Pubkey, program: &Pubkey) -> Result<()> {
    let key =
        Pubkey::find_program_address(&[user.as_ref(), program.as_ref(), mint.as_ref()], &ATA).0;
    require_keys_eq!(ai.key(), key, Error::Account);
    token(ai, mint, user, program)?;
    Ok(())
}
pub fn create_user_ata<'a>(
    payer: &AccountInfo<'a>,
    ata: &AccountInfo<'a>,
    mint: &AccountInfo<'a>,
    system: &AccountInfo<'a>,
    token_program: &AccountInfo<'a>,
    associated: &AccountInfo<'a>,
) -> Result<()> {
    use anchor_lang::solana_program::instruction::{AccountMeta, Instruction};
    require_keys_eq!(associated.key(), ATA, Error::Account);
    let ix = Instruction {
        program_id: ATA,
        accounts: vec![
            AccountMeta::new(payer.key(), true),
            AccountMeta::new(ata.key(), false),
            AccountMeta::new_readonly(payer.key(), false),
            AccountMeta::new_readonly(mint.key(), false),
            AccountMeta::new_readonly(system.key(), false),
            AccountMeta::new_readonly(token_program.key(), false),
        ],
        data: vec![1],
    };
    invoke(
        &ix,
        &[
            payer.clone(),
            ata.clone(),
            mint.clone(),
            system.clone(),
            token_program.clone(),
            associated.clone(),
        ],
    )?;
    user_ata(ata, payer.key, mint.key, token_program.key)
}
pub fn mint_check(ai: &AccountInfo, initial: bool) -> Result<()> {
    require_keys_eq!(*ai.owner, spl_token_2022_interface::ID, Error::Account);
    let data = ai.try_borrow_data()?;
    let m = StateWithExtensions::<Mint>::unpack(&data)?;
    require!(
        m.base.decimals == 6
            && m.base.is_initialized
            && m.base.mint_authority == COption::None
            && m.base.freeze_authority == COption::None,
        Error::Invariant
    );
    require!(
        if initial {
            m.base.supply == U
        } else {
            m.base.supply <= U
        },
        Error::Invariant
    ); // M1: burns only decrease supply
    require!(m.get_extension_types()?.len() == 2, Error::Invariant);
    let pointer = m.get_extension::<MetadataPointer>()?;
    require!(
        Option::<Pubkey>::from(pointer.authority).is_none()
            && Option::<Pubkey>::from(pointer.metadata_address) == Some(ai.key()),
        Error::Invariant
    );
    // Read the two fixed-offset fields of the Borsh TokenMetadata in place
    // (update_authority: 32 bytes, zero = None; then mint: 32 bytes). Deserializing
    // the whole value allocates its strings on the never-freed SBF heap on every
    // check, which exhausted the 32 KiB heap on a prefunded create_room + first buy.
    let metadata = m.get_extension_bytes::<TokenMetadata>()?;
    require!(metadata.len() >= 64, Error::Invariant);
    require!(
        metadata[..32].iter().all(|b| *b == 0) && metadata[32..64] == ai.key().to_bytes(),
        Error::Invariant
    );
    Ok(())
}
pub fn transfer<'a>(
    from: &AccountInfo<'a>,
    mint: &AccountInfo<'a>,
    to: &AccountInfo<'a>,
    authority: &AccountInfo<'a>,
    program: &AccountInfo<'a>,
    n: u64,
    seeds: Option<&[&[u8]]>,
    decimals: u8,
) -> Result<()> {
    let a = amount(from)?;
    let b = amount(to)?;
    let ix = spl_token_2022_interface::instruction::transfer_checked(
        program.key,
        from.key,
        mint.key,
        to.key,
        authority.key,
        &[],
        n,
        decimals,
    )?;
    let infos = [
        from.clone(),
        mint.clone(),
        to.clone(),
        authority.clone(),
        program.clone(),
    ];
    if let Some(s) = seeds {
        invoke_signed(&ix, &infos, &[s])?;
    } else {
        invoke(&ix, &infos)?;
    }
    require!(
        amount(from)? == sub(a, n)? && amount(to)? == add(b, n)?,
        Error::Invariant
    );
    Ok(())
}
pub fn create_token<'a>(
    user: &AccountInfo<'a>,
    ai: &AccountInfo<'a>,
    mint: &AccountInfo<'a>,
    authority: &Pubkey,
    system: &AccountInfo<'a>,
    program: &AccountInfo<'a>,
    seeds: &[&[u8]],
) -> Result<u8> {
    let bump = create_pda(user, ai, system, program.key, 165, 165, seeds)?;
    invoke(
        &spl_token_2022_interface::instruction::initialize_account3(
            program.key,
            ai.key,
            mint.key,
            authority,
        )?,
        &[ai.clone(), mint.clone(), program.clone()],
    )?;
    token(ai, mint.key, authority, program.key)?;
    Ok(bump)
}
#[allow(clippy::too_many_arguments)]
pub fn create_mint<'a>(
    user: &AccountInfo<'a>,
    ai: &AccountInfo<'a>,
    vault: &AccountInfo<'a>,
    authority: &AccountInfo<'a>,
    room_key: Pubkey,
    launch: &Launch,
    door: Option<(u32, u64)>,
    system: &AccountInfo<'a>,
    program: &AccountInfo<'a>,
    mint_seeds: &[&[u8]],
    vault_seeds: &[&[u8]],
    authority_seeds: &[&[u8]],
) -> Result<(u8, u8)> {
    let room = room_key.to_string();
    let mut extra = vec![("room".to_string(), room)];
    if let Some((i, nonce)) = door {
        // Self-describing door mint: room + door_nonce + program give the Door PDA
        // ["door", room, door_nonce u64 LE] with no scan. `door` is creation order only.
        extra.push(("door".to_string(), i.to_string()));
        extra.push(("door_nonce".to_string(), nonce.to_string()));
        extra.push(("program".to_string(), crate::ID.to_string()));
    }
    let meta_value = 64
        + 12
        + launch.name.len()
        + launch.symbol.len()
        + launch.uri.len()
        + 4
        + extra
            .iter()
            .map(|(k, v)| 8 + k.len() + v.len())
            .sum::<usize>();
    let bump = create_pda(
        user,
        ai,
        system,
        program.key,
        234,
        234 + 4 + meta_value,
        mint_seeds,
    )?;
    invoke(
        &spl_token_2022_interface::extension::metadata_pointer::instruction::initialize(
            program.key,
            ai.key,
            None,
            Some(ai.key()),
        )?,
        &[ai.clone(), program.clone()],
    )?;
    invoke(
        &spl_token_2022_interface::instruction::initialize_mint2(
            program.key,
            ai.key,
            authority.key,
            None,
            6,
        )?,
        &[ai.clone(), program.clone()],
    )?;
    invoke_signed(
        &meta::initialize(
            program.key,
            ai.key,
            authority.key,
            ai.key,
            authority.key,
            launch.name.clone(),
            launch.symbol.clone(),
            launch.uri.clone(),
        ),
        &[ai.clone(), authority.clone(), program.clone()],
        &[authority_seeds],
    )?;
    for (k, v) in extra {
        invoke_signed(
            &meta::update_field(program.key, ai.key, authority.key, Field::Key(k), v),
            &[ai.clone(), authority.clone(), program.clone()],
            &[authority_seeds],
        )?;
    }
    let vb = create_token(user, vault, ai, authority.key, system, program, vault_seeds)?;
    invoke_signed(
        &spl_token_2022_interface::instruction::mint_to_checked(
            program.key,
            ai.key,
            vault.key,
            authority.key,
            &[],
            U,
            6,
        )?,
        &[
            ai.clone(),
            vault.clone(),
            authority.clone(),
            program.clone(),
        ],
        &[authority_seeds],
    )?;
    invoke_signed(
        &spl_token_2022_interface::instruction::set_authority(
            program.key,
            ai.key,
            None,
            spl_token_2022_interface::instruction::AuthorityType::MintTokens,
            authority.key,
            &[],
        )?,
        &[ai.clone(), authority.clone(), program.clone()],
        &[authority_seeds],
    )?;
    invoke_signed(
        &meta::update_authority(program.key, ai.key, authority.key, Default::default()),
        &[ai.clone(), authority.clone(), program.clone()],
        &[authority_seeds],
    )?;
    mint_check(ai, true)?;
    require!(
        token(vault, ai.key, authority.key, program.key)? == U,
        Error::Invariant
    );
    Ok((bump, vb))
}
pub fn door_check(
    d: &Door,
    di: &AccountInfo,
    r: &Room,
    rkey: Pubkey,
    mint: &AccountInfo,
    vault: &AccountInfo,
    backing: &AccountInfo,
) -> Result<()> {
    require_keys_eq!(d.room, rkey, Error::Account);
    pda(di, &[b"door", rkey.as_ref(), &d.nonce.to_le_bytes()])?;
    require_keys_eq!(mint.key(), d.mint, Error::Account);
    require_keys_eq!(vault.key(), d.door_vault, Error::Account);
    require_keys_eq!(backing.key(), d.room_token_vault, Error::Account);
    mint_check(mint, false)?;
    require!(d.backing <= r.supply, Error::Invariant);
    // B1 inequalities point towards covering liabilities; never quote from these amounts.
    require!(
        token(vault, mint.key, di.key, &spl_token_2022_interface::ID)? >= sub(r.supply, d.backing)?,
        Error::Invariant
    );
    require!(
        token(backing, &r.room_mint, di.key, &spl_token_2022_interface::ID)? >= d.backing,
        Error::Invariant
    );
    Ok(())
}
pub fn core_check(c: &Core, local_door_fees: u64) -> Result<()> {
    room_check(
        &c.room,
        c.room.key(),
        &c.reserve,
        &c.fees,
        &c.room_vault,
        &c.retired,
        &c.room_mint,
        local_door_fees,
    )
}
pub fn room_check(
    r: &Room,
    key: Pubkey,
    reserve: &AccountInfo,
    fees: &AccountInfo,
    room_vault: &AccountInfo,
    retired: &AccountInfo,
    room_mint: &AccountInfo,
    local_door_fees: u64,
) -> Result<()> {
    require!(
        r.status <= 1 && r.sold <= r.supply && r.retired <= r.sold,
        Error::Invariant
    );
    require!(
        r.reserve >= r.curve(r.sold)? && r.reserve <= r.graduation_trigger_lamports,
        Error::Invariant
    ); // I1
    require!(
        (r.status == 1) == (r.reserve == r.graduation_trigger_lamports),
        Error::Invariant
    );
    mint_check(room_mint, false)?;
    require!(
        token(
            room_vault,
            &r.room_mint,
            &key,
            &spl_token_2022_interface::ID
        )? >= sub(r.supply, r.sold)?,
        Error::Invariant
    ); // S1
    require!(
        token(retired, &r.room_mint, &key, &spl_token_2022_interface::ID)? >= r.retired,
        Error::Invariant
    );
    let rent = Rent::get()?.minimum_balance(0);
    require!(
        sub(reserve.lamports(), rent)? >= r.reserve,
        Error::Invariant
    );
    let known = add(
        add(
            add(r.protocol_accrued_sol, r.pending_reserve_sol)?,
            r.founder_accrued,
        )?,
        local_door_fees,
    )?;
    require!(sub(fees.lamports(), rent)? >= known, Error::Invariant);
    // The global sum over doors is inductive: every path changes the vault and
    // the sum of its touched counters by exactly the same amount. No scan is needed.
    Ok(())
}
pub fn reserve_delta(before_l: u64, before_r: u64, c: &Core) -> Result<()> {
    require!(
        (c.reserve.lamports() as i128 - before_l as i128)
            == (c.room.reserve as i128 - before_r as i128),
        Error::Invariant
    );
    Ok(())
}
pub fn fee_delta(before_l: u64, after_l: u64, before_known: u128, after_known: u128) -> Result<()> {
    require!(
        after_l as i128 - before_l as i128 == after_known as i128 - before_known as i128,
        Error::Invariant
    );
    Ok(())
}
pub fn known(r: &Room, doors: &[&Door]) -> u128 {
    r.protocol_accrued_sol as u128
        + r.pending_reserve_sol as u128
        + r.founder_accrued as u128
        + doors.iter().map(|d| d.accrued_sol as u128).sum::<u128>()
}
pub fn read_slug(ai: &AccountInfo, identity: &[u8; 32]) -> Result<Option<SlugLock>> {
    pda(ai, &[b"slug", identity])?;
    if ai.data_is_empty() {
        require_keys_eq!(*ai.owner, anchor_lang::system_program::ID, Error::Account);
        return Ok(None);
    }
    require_keys_eq!(*ai.owner, crate::ID, Error::Account);
    Ok(Some(SlugLock::try_deserialize(
        &mut &ai.try_borrow_data()?[..],
    )?))
}
/// The lock's holder must be the canonical `Room` of `lock_room_id`, and not live. The room is read
/// in place (`RoomBytes`): owner, exact size and discriminator are what `Account<Room>` checked.
pub fn read_name(ai: &AccountInfo, key: &[u8; NAME_KEY_LEN]) -> Result<Option<NameLock>> {
    pda(ai, &[b"name", key])?;
    if ai.data_is_empty() {
        require_keys_eq!(*ai.owner, anchor_lang::system_program::ID, Error::Account);
        return Ok(None);
    }
    require_keys_eq!(*ai.owner, crate::ID, Error::Account);
    Ok(Some(NameLock::try_deserialize(
        &mut &ai.try_borrow_data()?[..],
    )?))
}
pub fn holder_dead(
    lock_room_id: u64,
    holder: Option<&AccountInfo>,
    c: &Config,
    now: i64,
) -> Result<()> {
    let holder = holder.ok_or(Error::Holder)?;
    require_keys_eq!(*holder.owner, crate::ID, Error::Holder);
    let data = holder.try_borrow_data()?;
    require!(
        data.len() == Room::LEN && data[..8] == *Room::DISCRIMINATOR,
        Error::Holder
    );
    let room = RoomBytes(&data);
    let expected = Pubkey::create_program_address(
        &[b"room", &room.room_id().to_le_bytes(), &[room.bump()]],
        &crate::ID,
    )
    .map_err(|_| error!(Error::Pda))?;
    require_keys_eq!(*holder.key, expected, Error::Pda);
    require!(lock_room_id == room.room_id(), Error::Holder);
    require!(!room.live(c, now)?, Error::Live);
    Ok(())
}
