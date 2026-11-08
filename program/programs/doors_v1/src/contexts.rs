use crate::{state::*, Error};
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct InitializeConfig<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(init,payer=admin,space=Config::LEN,seeds=[b"config"],bump)]
    pub config: Box<Account<'info, Config>>,
    pub program: Program<'info, crate::program::DoorsV1>,
    #[account(constraint=program.programdata_address()?==Some(program_data.key()) @ Error::Authority,
              constraint=program_data.upgrade_authority_address==Some(admin.key()) @ Error::Authority)]
    pub program_data: Account<'info, ProgramData>,
    pub system_program: Program<'info, System>,
}
#[derive(Accounts)]
pub struct UpdateConfig<'info> {
    pub admin: Signer<'info>,
    #[account(mut,seeds=[b"config"],bump=config.bump,has_one=admin)]
    pub config: Box<Account<'info, Config>>,
}
#[derive(Accounts)]
#[instruction(room_id:u64)]
pub struct CreateRoom<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(address=config.matcher_authority @ Error::Matcher)]
    pub matcher: Signer<'info>,
    #[account(seeds=[b"config"],bump=config.bump)]
    pub config: Box<Account<'info, Config>>,
    #[account(init,payer=user,space=Room::BIRTH_LEN,seeds=[b"room".as_ref(),room_id.to_le_bytes().as_ref()],bump)]
    pub room: Box<Account<'info, Room>>,
    /// CHECK: canonical PDA, created program-owned by the handler.
    #[account(mut)]
    pub reserve: UncheckedAccount<'info>,
    /// CHECK: canonical PDA, created program-owned by the handler.
    #[account(mut)]
    pub fees: UncheckedAccount<'info>,
    /// CHECK: canonical system-owned PDA, rent only; reserved for phase 2.
    #[account(mut)]
    pub grad_payer: UncheckedAccount<'info>,
    /// CHECK: identity-derived PDA, manually initialized or validated before takeover.
    #[account(mut)]
    pub slug: UncheckedAccount<'info>,
    /// CHECK: the dead holder of a lock being taken over; read in place by `vaults::holder_dead`.
    pub old_holder: Option<UncheckedAccount<'info>>,
    /// CHECK: PDA ["name", name_key], present iff name_key is; created by the handler, or validated
    /// and taken over from a dead holder.
    #[account(mut)]
    pub name_lock: Option<UncheckedAccount<'info>>,
    /// CHECK: the NameLock's dead holder when it is taken over; read in place by `vaults::holder_dead`.
    /// May be the same account as `old_holder`.
    pub old_name_holder: Option<UncheckedAccount<'info>>,
    /// CHECK: canonical Token-2022 mint, initialized and revoked atomically.
    #[account(mut)]
    pub room_mint: UncheckedAccount<'info>,
    /// CHECK: canonical token PDA created by handler.
    #[account(mut)]
    pub room_vault: UncheckedAccount<'info>,
    /// CHECK: canonical token PDA created by handler.
    #[account(mut)]
    pub retired: UncheckedAccount<'info>,
    /// CHECK: canonical classic native-WSOL token PDA created by handler.
    #[account(mut)]
    pub fee_wsol: UncheckedAccount<'info>,
    #[account(init,payer=user,space=Door::LEN,seeds=[b"door",room.key().as_ref(),&0u64.to_le_bytes()],bump)]
    pub door: Box<Account<'info, Door>>,
    /// CHECK: canonical Token-2022 mint, initialized and revoked atomically.
    #[account(mut)]
    pub door_mint: UncheckedAccount<'info>,
    /// CHECK: canonical token PDA created by handler.
    #[account(mut)]
    pub door_vault: UncheckedAccount<'info>,
    /// CHECK: canonical token PDA created by handler.
    #[account(mut)]
    pub backing: UncheckedAccount<'info>,
    /// CHECK: canonical user ATA when the optional first buy is nonzero.
    #[account(mut)]
    pub user_token: UncheckedAccount<'info>,
    /// CHECK: immutable, executable program id.
    #[account(address=spl_token_2022_interface::ID,executable)]
    pub token_program: UncheckedAccount<'info>,
    /// CHECK: immutable, executable classic SPL Token id, WSOL only.
    #[account(address=spl_token_interface::ID,executable)]
    pub classic_token_program: UncheckedAccount<'info>,
    /// CHECK: canonical native mint, validated by token CPI.
    #[account(address=spl_token_interface::native_mint::ID)]
    pub wsol_mint: UncheckedAccount<'info>,
    /// CHECK: fixed executable ATA program, for atomic optional first buy.
    #[account(address=crate::vaults::ATA,executable)]
    pub associated_token_program: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}

// Every live curve path validates the same immutable room/vault identities.
#[derive(Accounts)]
pub struct Core<'info> {
    #[account(seeds=[b"config"],bump=config.bump)]
    pub config: Box<Account<'info, Config>>,
    #[account(mut,seeds=[b"room",&room.room_id.to_le_bytes()],bump=room.bumps[0])]
    pub room: Box<Account<'info, Room>>,
    /// CHECK: canonical program-owned empty reserve PDA, checked by invariants too.
    #[account(mut,seeds=[b"reserve",room.key().as_ref()],bump=room.bumps[1])]
    pub reserve: UncheckedAccount<'info>,
    /// CHECK: canonical program-owned empty fee PDA.
    #[account(mut,seeds=[b"fees",room.key().as_ref()],bump=room.bumps[2])]
    pub fees: UncheckedAccount<'info>,
    /// CHECK: fixed mint and authorities validated on every affected path.
    #[account(address=room.room_mint)]
    pub room_mint: UncheckedAccount<'info>,
    /// CHECK: fixed address plus mint, owner and balance validated by invariants.
    #[account(mut,address=room.room_vault)]
    pub room_vault: UncheckedAccount<'info>,
    /// CHECK: fixed address plus mint, owner and balance validated by invariants.
    #[account(mut,address=room.retired_vault)]
    pub retired: UncheckedAccount<'info>,
}
#[derive(Accounts)]
pub struct TradeAccounts<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    pub core: Core<'info>,
    #[account(mut)]
    pub door: Option<Box<Account<'info, Door>>>,
    /// CHECK: required and validated for door route, must be None on room route.
    pub door_mint: Option<UncheckedAccount<'info>>,
    /// CHECK: required and validated for door route.
    #[account(mut)]
    pub door_vault: Option<UncheckedAccount<'info>>,
    /// CHECK: required and validated for door route.
    #[account(mut)]
    pub backing: Option<UncheckedAccount<'info>>,
    /// CHECK: canonical user ATA validated for selected mint.
    #[account(mut)]
    pub user_token: UncheckedAccount<'info>,
    /// CHECK: executable Token-2022 program.
    #[account(address=spl_token_2022_interface::ID,executable)]
    pub token_program: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}
#[derive(Accounts)]
#[instruction(launch:Launch)]
pub struct OpenDoor<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(address=core.config.matcher_authority @ Error::Matcher)]
    pub matcher: Signer<'info>,
    pub core: Core<'info>,
    /// CHECK: derived from launch metadata, existing lock validated even when not selected.
    pub slug: UncheckedAccount<'info>,
    /// CHECK: the dead holder of a lock being taken over; read in place by `vaults::holder_dead`.
    pub old_holder: Option<UncheckedAccount<'info>>,
    #[account(init,payer=user,space=Door::LEN,seeds=[b"door",core.room.key().as_ref(),&launch.door_nonce.to_le_bytes()],bump)]
    pub door: Box<Account<'info, Door>>,
    /// CHECK: canonical Token-2022 mint created in handler.
    #[account(mut)]
    pub door_mint: UncheckedAccount<'info>,
    /// CHECK: canonical token PDA created in handler.
    #[account(mut)]
    pub door_vault: UncheckedAccount<'info>,
    /// CHECK: canonical token PDA created in handler.
    #[account(mut)]
    pub backing: UncheckedAccount<'info>,
    /// CHECK: canonical user ATA on optional first buy.
    #[account(mut)]
    pub user_token: UncheckedAccount<'info>,
    /// CHECK: executable Token-2022 program.
    #[account(address=spl_token_2022_interface::ID,executable)]
    pub token_program: UncheckedAccount<'info>,
    /// CHECK: fixed executable ATA program, for atomic optional first buy.
    #[account(address=crate::vaults::ATA,executable)]
    pub associated_token_program: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}
#[derive(Accounts)]
pub struct SwapDoors<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    pub core: Core<'info>,
    #[account(mut)]
    pub door_a: Box<Account<'info, Door>>,
    #[account(mut)]
    pub door_b: Box<Account<'info, Door>>,
    /// CHECK: validated by B1 and mint validation.
    pub mint_a: UncheckedAccount<'info>,
    /// CHECK: validated by B1 and mint validation.
    pub mint_b: UncheckedAccount<'info>,
    /// CHECK: validated by B1.
    #[account(mut)]
    pub vault_a: UncheckedAccount<'info>,
    /// CHECK: validated by B1.
    #[account(mut)]
    pub vault_b: UncheckedAccount<'info>,
    /// CHECK: validated by B1.
    #[account(mut)]
    pub backing_a: UncheckedAccount<'info>,
    /// CHECK: validated by B1.
    #[account(mut)]
    pub backing_b: UncheckedAccount<'info>,
    /// CHECK: canonical user ATA for mint A.
    #[account(mut)]
    pub user_a: UncheckedAccount<'info>,
    /// CHECK: canonical user ATA for mint B.
    #[account(mut)]
    pub user_b: UncheckedAccount<'info>,
    /// CHECK: canonical room-token fee vault, created on the first swap or validated.
    #[account(mut)]
    pub swap_fees: UncheckedAccount<'info>,
    /// CHECK: executable Token-2022 program.
    #[account(address=spl_token_2022_interface::ID,executable)]
    pub token_program: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}
#[derive(Accounts)]
pub struct ClaimSwapFees<'info> {
    pub authority: Signer<'info>,
    pub core: Core<'info>,
    #[account(mut)]
    pub door: Option<Box<Account<'info, Door>>>,
    /// CHECK: required and validated with the door on door fee claims.
    pub door_mint: Option<UncheckedAccount<'info>>,
    /// CHECK: required and validated with the door on door fee claims.
    pub door_vault: Option<UncheckedAccount<'info>>,
    /// CHECK: required and validated with the door on door fee claims.
    pub backing: Option<UncheckedAccount<'info>>,
    /// CHECK: canonical room-token fee vault, validated by the handler.
    #[account(mut)]
    pub swap_fees: UncheckedAccount<'info>,
    /// CHECK: canonical room-token ATA of the entitled signer.
    #[account(mut)]
    pub recipient_token: UncheckedAccount<'info>,
    /// CHECK: executable Token-2022 program.
    #[account(address=spl_token_2022_interface::ID,executable)]
    pub token_program: UncheckedAccount<'info>,
}
#[derive(Accounts)]
pub struct Retire<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
    pub core: Core<'info>,
    /// CHECK: fixed RetiredVault, writable counterpart of core.retired.
    #[account(mut,address=core.room.retired_vault)]
    pub retired_output: UncheckedAccount<'info>,
    /// CHECK: executable Token-2022 program.
    #[account(address=spl_token_2022_interface::ID,executable)]
    pub token_program: UncheckedAccount<'info>,
}
#[derive(Accounts)]
pub struct Claim<'info> {
    pub system_program: Program<'info, System>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub core: Core<'info>,
    #[account(mut)]
    pub door: Option<Box<Account<'info, Door>>>,
    /// CHECK: if a door is provided, all three B1 accounts are required.
    pub door_mint: Option<UncheckedAccount<'info>>,
    /// CHECK: if a door is provided, all three B1 accounts are required.
    pub door_vault: Option<UncheckedAccount<'info>>,
    /// CHECK: if a door is provided, all three B1 accounts are required.
    pub backing: Option<UncheckedAccount<'info>>,
    /// CHECK: validated canonical room WSOL vault.
    #[account(mut,address=core.room.fee_wsol)]
    pub fee_wsol: UncheckedAccount<'info>,
    /// CHECK: canonical native mint.
    #[account(address=spl_token_interface::native_mint::ID)]
    pub wsol_mint: UncheckedAccount<'info>,
    /// CHECK: exact recipient authority or Config.protocol_fee_recipient in handler.
    #[account(mut)]
    pub recipient: UncheckedAccount<'info>,
    /// CHECK: canonical WSOL ATA of recipient.
    #[account(mut)]
    pub recipient_wsol: UncheckedAccount<'info>,
    /// CHECK: executable classic SPL Token, for WSOL only.
    #[account(address=spl_token_interface::ID,executable)]
    pub classic_token_program: UncheckedAccount<'info>,
}
#[derive(Accounts)]
pub struct SetRecipient<'info> {
    pub authority: Signer<'info>,
    pub core: Core<'info>,
    #[account(mut)]
    pub door: Box<Account<'info, Door>>,
    /// CHECK: B1/M1 validated in handler.
    pub door_mint: UncheckedAccount<'info>,
    /// CHECK: B1 validated in handler.
    pub door_vault: UncheckedAccount<'info>,
    /// CHECK: B1 validated in handler.
    pub backing: UncheckedAccount<'info>,
}
#[derive(Accounts)]
pub struct ReleaseSlug<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,
    #[account(seeds=[b"config"],bump=config.bump)]
    pub config: Box<Account<'info, Config>>,
    #[account(seeds=[b"room",&room.room_id.to_le_bytes()],bump=room.bumps[0])]
    pub room: Box<Account<'info, Room>>,
    #[account(mut,close=caller,seeds=[b"slug",room.identity.as_ref()],bump=slug.bump,
              constraint=slug.room_id==room.room_id @ Error::Identity)]
    pub slug: Account<'info, SlugLock>,
}
#[derive(Accounts)]
pub struct ReleaseName<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,
    #[account(seeds=[b"config"],bump=config.bump)]
    pub config: Box<Account<'info, Config>>,
    #[account(seeds=[b"room",&room.room_id.to_le_bytes()],bump=room.bumps[0])]
    pub room: Box<Account<'info, Room>>,
    #[account(mut,close=caller,seeds=[b"name",name_lock.key.as_ref()],bump=name_lock.bump,
              constraint=name_lock.room_id==room.room_id @ Error::Identity)]
    pub name_lock: Account<'info, NameLock>,
}
#[derive(Accounts)]
pub struct ProposeGate<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(seeds=[b"config"],bump=config.bump,has_one=admin)]
    pub config: Box<Account<'info, Config>>,
    /// CHECK: PDA ["gate"]; created by the handler, or validated and overwritten when it exists.
    #[account(mut)]
    pub pending: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}
#[derive(Accounts)]
pub struct ApplyGate<'info> {
    #[account(mut,seeds=[b"config"],bump=config.bump)]
    pub config: Box<Account<'info, Config>>,
    #[account(mut,close=admin,seeds=[b"gate"],bump=pending.bump)]
    pub pending: Account<'info, PendingGate>,
    /// CHECK: receives the pending account's rent; must be the current admin.
    #[account(mut,address=config.admin @ Error::Authority)]
    pub admin: UncheckedAccount<'info>,
}
#[derive(Accounts)]
pub struct CancelGate<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(seeds=[b"config"],bump=config.bump,has_one=admin)]
    pub config: Box<Account<'info, Config>>,
    #[account(mut,close=admin,seeds=[b"gate"],bump=pending.bump)]
    pub pending: Account<'info, PendingGate>,
}
