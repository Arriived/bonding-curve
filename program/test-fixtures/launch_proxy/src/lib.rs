//! Test-only untrusted CPI proxy; never deployed by the application.
use anchor_lang::solana_program::{
    account_info::AccountInfo, entrypoint, entrypoint::ProgramResult,
    instruction::{AccountMeta, Instruction}, program::invoke, pubkey::Pubkey,
};
entrypoint!(process);
fn process(_id:&Pubkey,accounts:&[AccountInfo],data:&[u8])->ProgramResult {
    let target=&accounts[0];
    let metas=accounts[1..].iter().map(|a|AccountMeta{pubkey:*a.key,is_signer:a.is_signer,is_writable:a.is_writable}).collect();
    invoke(&Instruction{program_id:*target.key,accounts:metas,data:data.to_vec()},accounts)
}
