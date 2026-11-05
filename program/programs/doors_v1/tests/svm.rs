//! All instruction tests execute the compiled SBF ELF, with real SPL programs
//! and Ed25519 verification. No native replacement of the Anchor entrypoint.
use anchor_lang::solana_program::program_pack::Pack;
use anchor_lang::solana_program::{bpf_loader_upgradeable, program_option::COption};
use anchor_lang::{
    prelude::Pubkey, AccountDeserialize, AccountSerialize, InstructionData, ToAccountMetas,
};
use doors_v1::{accounts as a, instruction as ix, math::U, state::*, vaults::ATA, ID};
use litesvm::{types::TransactionMetadata, LiteSVM};
use serde_json::{json, Value};
use solana_account::Account;
use solana_clock::Clock;
use solana_compute_budget_interface::ComputeBudgetInstruction;
use solana_instruction::{AccountMeta, Instruction};
use solana_keypair::Keypair;
use solana_message::Message;
use solana_signer::Signer;
use solana_transaction::Transaction;
use spl_token_2022_interface::{
    extension::{BaseStateWithExtensions, StateWithExtensions},
    state::{Account as TokenAccount, Mint},
};
use std::{collections::BTreeMap, path::PathBuf};

include!("cases/sweeps.rs");
include!("cases/liveness_delay.rs");

fn p(seeds: &[&[u8]]) -> Pubkey {
    Pubkey::find_program_address(seeds, &ID).0
}
fn ata(owner: Pubkey, mint: Pubkey, program: Pubkey) -> Pubkey {
    Pubkey::find_program_address(&[owner.as_ref(), program.as_ref(), mint.as_ref()], &ATA).0
}
fn instr<T: InstructionData, A: ToAccountMetas>(acc: A, args: T) -> Instruction {
    Instruction {
        program_id: ID,
        accounts: acc.to_account_metas(None),
        data: args.data(),
    }
}
fn launch(name: &str) -> Launch {
    Launch {
        name: name.into(),
        symbol: "MEME".into(),
        uri: "https://example.invalid/m.json".into(),
        first_buy_lamports: 0,
        min_tokens_out: 0,
        matcher_version: 1,
        rule: 0,
        face: 0,
        max_fee_lamports: 0,
        expected_terms_hash: [0; 32],
        // 0 = filled by the fixture: door nonce from room state, expiry from the VM clock.
        door_nonce: 0,
        expires_at_slot: 0,
    }
}
fn defaults(matcher: Pubkey, recipient: Pubkey) -> Settings {
    let q: Value = serde_json::from_str(include_str!(
        "../../../../research/doors_into_one_room/outputs/curve_quantities.json"
    ))
    .unwrap();
    Settings {
        protocol_fee_recipient: recipient,
        fee_bps: 100,
        door_share_bps: 6000,
        door_fee_lamports: 0,
        room_fee_lamports: 0,
        convert_fee_lamports: 0,
        v_sol_lamports: q["v_sol_lamports"].as_u64().unwrap(),
        v_tok: q["v_tok_base"].as_u64().unwrap(),
        supply: U,
        r_star_lamports: 85_000_000_000,
        meteora_dynamic_config: Pubkey::default(),
        graduation_trigger_lamports: q["trigger"].as_u64().unwrap(),
        paused: false,
        matcher_authority: matcher,
        live_min_reserve_lamports: 500_000_000,
        live_max_idle_seconds: 21600,
        live_new_seconds: 3600,
        live_min_volume_lamports: 5_000_000_000,
        pool_min_window_lp_fee: 80_000_000,
        founder_share_bps: 0,
    }
}
#[derive(Clone)]
struct DoorKeys {
    door: Pubkey,
    mint: Pubkey,
    vault: Pubkey,
    backing: Pubkey,
    user: Pubkey,
}
impl DoorKeys {
    fn new(room: Pubkey, nonce: u64, user: Pubkey) -> Self {
        let door = p(&[b"door", room.as_ref(), &nonce.to_le_bytes()]);
        let mint = p(&[b"door_mint", room.as_ref(), &nonce.to_le_bytes()]);
        Self {
            door,
            mint,
            vault: p(&[b"door_vault", door.as_ref()]),
            backing: p(&[b"door_room_vault", door.as_ref()]),
            user: ata(user, mint, spl_token_2022_interface::ID),
        }
    }
}
struct Fixture {
    svm: LiteSVM,
    user: Keypair,
    matcher: Keypair,
    cfg: Pubkey,
    rid: u64,
    room: Pubkey,
    doors: Vec<DoorKeys>,
    cus: BTreeMap<String, Vec<u64>>,
    operations: u64,
}
impl Fixture {
    fn empty(founder_bps: u16) -> Self {
        // Public, deterministic fixture secrets: never use these keys outside tests.
        let user = Keypair::new_from_array([11; 32]);
        let matcher = Keypair::new_from_array([22; 32]);
        let mut svm = LiteSVM::new()
            .with_transaction_history(0)
            .with_log_bytes_limit(None);
        // LiteSVM bundles token programs, but does not populate the native mint.
        // Match the canonical initialized classic-SPL native-mint account.
        let native = spl_token_interface::state::Mint {
            decimals: 9,
            is_initialized: true,
            ..Default::default()
        };
        let mut data = vec![0; spl_token_interface::state::Mint::LEN];
        spl_token_interface::state::Mint::pack(native, &mut data).unwrap();
        svm.set_account(
            spl_token_interface::native_mint::ID,
            Account {
                lamports: svm.minimum_balance_for_rent_exemption(data.len()),
                data,
                owner: spl_token_interface::ID,
                executable: false,
                rent_epoch: 0,
            },
        )
        .unwrap();
        let elf = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../target/deploy/doors_v1.so");
        svm.add_program(ID, &std::fs::read(elf).expect("run cargo build-sbf first"))
            .unwrap();
        svm.airdrop(&user.pubkey(), 1_000_000_000_000).unwrap();
        svm.airdrop(&matcher.pubkey(), 1_000_000_000).unwrap();
        let pd = bpf_loader_upgradeable::get_program_data_address(&ID);
        let mut pd_account = svm.get_account(&pd).unwrap();
        pd_account.data[12] = 1;
        pd_account.data[13..45].copy_from_slice(user.pubkey().as_ref());
        svm.set_account(pd, pd_account).unwrap();
        let mut clock = svm.get_sysvar::<Clock>();
        clock.unix_timestamp = 1_800_000_000;
        svm.set_sysvar(&clock);
        let cfg = p(&[b"config"]);
        let rid: u64 = 0xd35a_e081_6ab4_9c27;
        let room = p(&[b"room", &rid.to_le_bytes()]);
        let mut f = Self {
            svm,
            user,
            matcher,
            cfg,
            rid,
            room,
            doors: vec![],
            cus: BTreeMap::new(),
            operations: 0,
        };
        let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
        settings.founder_share_bps = founder_bps;
        let init = instr(
            a::InitializeConfig {
                admin: f.user.pubkey(),
                config: cfg,
                program: ID,
                program_data: pd,
                system_program: anchor_lang::system_program::ID,
            },
            ix::InitializeConfig { settings },
        );
        f.send(init, false, "initialize_config");
        f
    }
    fn new(founder_bps: u16) -> Self {
        let mut f = Self::empty(founder_bps);
        f.create(launch("First room"), None);
        f
    }
    fn send(&mut self, ix: Instruction, matcher: bool, name: &str) -> TransactionMetadata {
        let measure_program = ix.program_id == ID;
        let tx = Transaction::new(
            &if matcher {
                vec![&self.user, &self.matcher]
            } else {
                vec![&self.user]
            },
            Message::new(
                &[
                    ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                    ix,
                ],
                Some(&self.user.pubkey()),
            ),
            self.svm.latest_blockhash(),
        );
        let meta = self
            .svm
            .send_transaction(tx)
            .unwrap_or_else(|e| panic!("{name}: {e:#?}"));
        // Inclusive CU for this program and its CPIs, excluding the separate
        // compute-budget instruction. Match the runtime's top-level program log.
        let prefix = format!("Program {ID} consumed ");
        let root_cu = meta.logs.iter().find_map(|line| {
            line.strip_prefix(&prefix)
                .and_then(|s| s.split_whitespace().next())
                .and_then(|n| n.parse::<u64>().ok())
        });
        let program_cu = if measure_program {
            root_cu.expect("runtime must report program-inclusive CU")
        } else {
            meta.compute_units_consumed
        };
        self.cus.entry(name.into()).or_default().push(program_cu);
        self.operations += 1;
        meta
    }
    fn fail(&mut self, ix: Instruction, matcher: bool) {
        self.fail_error(ix, matcher, None);
    }
    fn fail_error(&mut self, ix: Instruction, matcher: bool, code: Option<&str>) {
        let before: BTreeMap<_, _> = ix
            .accounts
            .iter()
            .map(|a| (a.pubkey, self.svm.get_account(&a.pubkey)))
            .collect();
        let tx = Transaction::new(
            &if matcher {
                vec![&self.user, &self.matcher]
            } else {
                vec![&self.user]
            },
            Message::new(
                &[
                    ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                    ix,
                ],
                Some(&self.user.pubkey()),
            ),
            self.svm.latest_blockhash(),
        );
        let failure = self
            .svm
            .send_transaction(tx)
            .expect_err("must reject invalid instruction");
        let reason = format!("{:?}", failure.err);
        assert!(reason.contains("Custom("), "{failure:#?}");
        if let Some(code) = code {
            assert!(
                failure
                    .meta
                    .logs
                    .iter()
                    .any(|line| line.contains(&format!("Error Code: {code}."))),
                "{failure:#?}"
            );
        }
        assert!(
            !reason.contains("ComputationalBudgetExceeded") && !reason.contains("MaxInstructionTraceLengthExceeded"),
            "resource exhaustion must not stand in for the expected validation failure: {failure:#?}"
        );
        for (key, account) in before {
            // The fee payer still pays the network fee on a failed transaction.
            if key != self.user.pubkey() {
                assert_eq!(
                    account,
                    self.svm.get_account(&key),
                    "failed instruction changed {key}"
                );
            }
        }
    }
    /// A deterministic, non-zero door nonce for the next door of this fixture's room.
    /// Production nonces are random; tests need the same value in open_ix and open.
    fn next_door_nonce(&self) -> u64 {
        (self.r().door_count as u64 + 1).wrapping_mul(0x9e37_79b9_7f4a_7c15)
    }
    /// Fill the fixture defaults: door nonce and an expiry one full window ahead.
    fn fill(&self, mut l: Launch, door: bool) -> Launch {
        if door && l.door_nonce == 0 {
            l.door_nonce = self.next_door_nonce();
        }
        if l.expires_at_slot == 0 {
            l.expires_at_slot = self.svm.get_sysvar::<Clock>().slot + MAX_LAUNCH_WINDOW_SLOTS;
        }
        l
    }
    fn create_ix(&self, l: Launch, holder: Option<Pubkey>) -> Instruction {
        let mut l = self.fill(l, false);
        let config = self.svm.get_account(&self.cfg).unwrap();
        l.expected_terms_hash = Config::try_deserialize(&mut &config.data[..])
            .unwrap()
            .launch_terms_hash();
        let d = DoorKeys::new(self.room, 0, self.user.pubkey());
        instr(
            a::CreateRoom {
                user: self.user.pubkey(),
                matcher: self.matcher.pubkey(),
                config: self.cfg,
                room: self.room,
                reserve: p(&[b"reserve", self.room.as_ref()]),
                fees: p(&[b"fees", self.room.as_ref()]),
                grad_payer: p(&[b"grad_payer", self.room.as_ref()]),
                slug: p(&[b"slug", &l.identity()]),
                old_holder: holder,
                room_mint: p(&[b"room_mint", self.room.as_ref()]),
                room_vault: p(&[b"room_vault", self.room.as_ref()]),
                retired: p(&[b"retired", self.room.as_ref()]),
                fee_wsol: p(&[b"fee_wsol", self.room.as_ref()]),
                door: d.door,
                door_mint: d.mint,
                door_vault: d.vault,
                backing: d.backing,
                user_token: d.user,
                token_program: spl_token_2022_interface::ID,
                classic_token_program: spl_token_interface::ID,
                wsol_mint: spl_token_interface::native_mint::ID,
                associated_token_program: ATA,
                system_program: anchor_lang::system_program::ID,
            },
            ix::CreateRoom {
                room_id: self.rid,
                launch: l,
            },
        )
    }
    fn create(&mut self, l: Launch, holder: Option<Pubkey>) {
        self.send(self.create_ix(l, holder), true, "create_room");
        self.doors
            .push(DoorKeys::new(self.room, 0, self.user.pubkey()));
        self.make_ata(self.doors[0].mint, spl_token_2022_interface::ID);
        self.make_ata(self.r().room_mint, spl_token_2022_interface::ID);
        self.make_ata(
            spl_token_interface::native_mint::ID,
            spl_token_interface::ID,
        );
        self.audit();
    }
    fn core(&self) -> a::Core {
        let r = self.r();
        a::Core {
            config: self.cfg,
            room: self.room,
            reserve: p(&[b"reserve", self.room.as_ref()]),
            fees: p(&[b"fees", self.room.as_ref()]),
            room_mint: r.room_mint,
            room_vault: r.room_vault,
            retired: r.retired_vault,
        }
    }
    fn open_ix(&self, l: Launch, holder: Option<Pubkey>) -> Instruction {
        let l = self.fill(l, true);
        let d = DoorKeys::new(self.room, l.door_nonce, self.user.pubkey());
        instr(
            a::OpenDoor {
                user: self.user.pubkey(),
                matcher: self.matcher.pubkey(),
                core: self.core(),
                slug: p(&[b"slug", &l.identity()]),
                old_holder: holder,
                door: d.door,
                door_mint: d.mint,
                door_vault: d.vault,
                backing: d.backing,
                user_token: d.user,
                token_program: spl_token_2022_interface::ID,
                associated_token_program: ATA,
                system_program: anchor_lang::system_program::ID,
            },
            ix::OpenDoor { launch: l },
        )
    }
    fn open(&mut self, l: Launch) {
        let l = self.fill(l, true);
        let d = DoorKeys::new(self.room, l.door_nonce, self.user.pubkey());
        self.checked(self.open_ix(l, None), true, "open_door");
        self.doors.push(d.clone());
        self.make_ata(d.mint, spl_token_2022_interface::ID);
        self.audit();
    }
    fn make_ata(&mut self, mint: Pubkey, program: Pubkey) {
        let owner = self.user.pubkey();
        let address = ata(owner, mint, program);
        let ix = Instruction {
            program_id: ATA,
            accounts: vec![
                AccountMeta::new(owner, true),
                AccountMeta::new(address, false),
                AccountMeta::new_readonly(owner, false),
                AccountMeta::new_readonly(mint, false),
                AccountMeta::new_readonly(anchor_lang::system_program::ID, false),
                AccountMeta::new_readonly(program, false),
            ],
            data: vec![1],
        };
        self.send(ix, false, "create_ata");
    }
    fn c(&self) -> Config {
        Config::try_deserialize(&mut &self.svm.get_account(&self.cfg).unwrap().data[..]).unwrap()
    }
    fn r(&self) -> Room {
        Room::try_deserialize(&mut &self.svm.get_account(&self.room).unwrap().data[..]).unwrap()
    }
    fn d(&self, i: usize) -> Door {
        Door::try_deserialize(&mut &self.svm.get_account(&self.doors[i].door).unwrap().data[..])
            .unwrap()
    }
    fn balance(&self, key: Pubkey) -> u64 {
        StateWithExtensions::<TokenAccount>::unpack(&self.svm.get_account(&key).unwrap().data)
            .unwrap()
            .base
            .amount
    }
    fn trade_ix(&self, door: Option<usize>, buy: bool, n: u64, min: u64) -> Instruction {
        let d = door.map(|i| &self.doors[i]);
        let c = self.core();
        let user_token = d.map_or_else(
            || {
                ata(
                    self.user.pubkey(),
                    c.room_mint,
                    spl_token_2022_interface::ID,
                )
            },
            |d| d.user,
        );
        let ac = a::TradeAccounts {
            user: self.user.pubkey(),
            core: c,
            door: d.map(|d| d.door),
            door_mint: d.map(|d| d.mint),
            door_vault: d.map(|d| d.vault),
            backing: d.map(|d| d.backing),
            user_token,
            token_program: spl_token_2022_interface::ID,
            system_program: anchor_lang::system_program::ID,
        };
        if buy {
            instr(
                ac,
                ix::Buy {
                    lamports_in: n,
                    min_tokens_out: min,
                },
            )
        } else {
            instr(
                ac,
                ix::Sell {
                    tokens_in: n,
                    min_lamports_out: min,
                },
            )
        }
    }
    fn trade(&mut self, door: Option<usize>, buy: bool, n: u64) {
        let name = match (buy, door.is_some()) {
            (true, true) => "buy_door",
            (false, true) => "sell_door",
            (true, false) => "buy_room",
            _ => "sell_room",
        };
        self.checked(self.trade_ix(door, buy, n, 0), false, name);
        self.audit();
    }
    fn checked(&mut self, ix: Instruction, matcher: bool, name: &str) -> TransactionMetadata {
        let r = self.r();
        let reserve = p(&[b"reserve", self.room.as_ref()]);
        let before = self.svm.get_account(&reserve).unwrap().lamports;
        let meta = self.send(ix, matcher, name);
        let after = self.r();
        assert_eq!(
            self.svm.get_account(&reserve).unwrap().lamports as i128 - before as i128,
            after.reserve as i128 - r.reserve as i128,
            "I2 ReserveVault delta in {name}"
        );
        meta
    }
    fn convert_ix(&self, from: usize, to: usize, n: u64) -> Instruction {
        let x = &self.doors[from];
        let y = &self.doors[to];
        instr(
            a::Convert {
                user: self.user.pubkey(),
                core: self.core(),
                door_a: x.door,
                door_b: y.door,
                mint_a: x.mint,
                mint_b: y.mint,
                vault_a: x.vault,
                vault_b: y.vault,
                backing_a: x.backing,
                backing_b: y.backing,
                user_a: x.user,
                user_b: y.user,
                token_program: spl_token_2022_interface::ID,
                system_program: anchor_lang::system_program::ID,
            },
            ix::Convert {
                amount: n,
                max_fee_lamports: 0,
            },
        )
    }
    fn convert(&mut self, from: usize, to: usize, n: u64) {
        let r = self.r();
        self.checked(self.convert_ix(from, to, n), false, "convert");
        assert_eq!(self.r().sold, r.sold);
        assert_eq!(self.r().reserve, r.reserve);
        self.audit();
    }
    fn retire(&mut self) {
        let c = self.core();
        let output = c.retired;
        self.checked(
            instr(
                a::Retire {
                    core: c,
                    retired_output: output,
                    token_program: spl_token_2022_interface::ID,
                },
                ix::RetirePending {},
            ),
            false,
            "retire_pending",
        );
        self.audit();
    }
    fn claim_ix(&self, kind: u8, door: usize, recipient: Pubkey) -> Instruction {
        let d = if kind == 0 {
            Some(&self.doors[door])
        } else {
            None
        };
        let ac = a::Claim {
            authority: self.user.pubkey(),
            core: self.core(),
            door: d.map(|d| d.door),
            door_mint: d.map(|d| d.mint),
            door_vault: d.map(|d| d.vault),
            backing: d.map(|d| d.backing),
            fee_wsol: self.r().fee_wsol,
            wsol_mint: spl_token_interface::native_mint::ID,
            recipient,
            recipient_wsol: ata(
                recipient,
                spl_token_interface::native_mint::ID,
                spl_token_interface::ID,
            ),
            classic_token_program: spl_token_interface::ID,
        };
        match kind {
            0 => instr(ac, ix::ClaimDoorFees {}),
            1 => instr(ac, ix::ClaimFounderFees {}),
            _ => instr(ac, ix::SweepProtocolFees {}),
        }
    }
    fn claim(&mut self, kind: u8, door: usize) {
        let name = match kind {
            0 => "claim_door_fees",
            1 => "claim_founder_fees",
            _ => "sweep_protocol_fees",
        };
        self.checked(self.claim_ix(kind, door, self.user.pubkey()), false, name);
        self.audit();
    }
    fn audit(&self) {
        let r = self.r();
        assert_eq!(
            self.svm.get_account(&self.room).unwrap().data.len(),
            Room::LEN
        );
        assert!(r.status <= 1);
        assert!(r.sold <= U && r.retired <= r.sold);
        assert!(r.reserve >= r.curve(r.sold).unwrap());
        assert!(r.reserve <= r.graduation_trigger_lamports);
        assert_eq!(r.status == 1, r.reserve == r.graduation_trigger_lamports);
        assert!(self.balance(r.room_vault) >= U - r.sold);
        assert!(self.balance(r.retired_vault) >= r.retired);
        let rent = self.svm.minimum_balance_for_rent_exemption(0);
        assert!(
            self.svm
                .get_account(&p(&[b"reserve", self.room.as_ref()]))
                .unwrap()
                .lamports
                - rent
                >= r.reserve
        );
        let mut fees = r.protocol_accrued_sol as u128
            + r.pending_reserve_sol as u128
            + r.founder_accrued as u128;
        let mut wfees = r.protocol_accrued_wsol as u128
            + r.pending_reserve_wsol as u128
            + r.founder_accrued_wsol as u128;
        for (key, account) in self.svm.get_program_accounts(&ID) {
            if let Ok(d) = Door::try_deserialize(&mut &account.data[..]) {
                if d.room != self.room {
                    continue;
                }
                assert_eq!(account.data.len(), Door::LEN);
                assert!(d.backing <= U);
                assert!(self.balance(d.room_token_vault) >= d.backing);
                assert!(self.balance(d.door_vault) >= U - d.backing);
                fees += d.accrued_sol as u128;
                wfees += d.accrued_wsol as u128;
                self.audit_mint(d.mint);
                assert_eq!(
                    key,
                    p(&[b"door", self.room.as_ref(), &d.nonce.to_le_bytes()])
                );
                self.audit_door_metadata(key, &d);
            }
        }
        assert!(
            (self
                .svm
                .get_account(&p(&[b"fees", self.room.as_ref()]))
                .unwrap()
                .lamports
                - rent) as u128
                >= fees
        );
        assert!(self.balance(r.fee_wsol) as u128 >= wfees);
        self.audit_mint(r.room_mint);
    }
    fn audit_mint(&self, mint: Pubkey) {
        let account = self.svm.get_account(&mint).unwrap();
        let m = StateWithExtensions::<Mint>::unpack(&account.data).unwrap();
        assert_eq!(m.get_extension_types().unwrap().len(), 2);
        assert_eq!(m.base.mint_authority, COption::None);
        assert_eq!(m.base.freeze_authority, COption::None);
        assert!(m.base.supply <= U);
        let metadata = m
            .get_variable_len_extension::<spl_token_metadata_interface::state::TokenMetadata>()
            .unwrap();
        assert_eq!(Option::<Pubkey>::from(metadata.update_authority), None);
        let total: u128 = self
            .svm
            .get_program_accounts(&spl_token_2022_interface::ID)
            .iter()
            .filter_map(|(_, a)| {
                StateWithExtensions::<TokenAccount>::unpack(&a.data)
                    .ok()
                    .filter(|a| a.base.mint == mint)
                    .map(|a| a.base.amount as u128)
            })
            .sum();
        assert_eq!(
            total, m.base.supply as u128,
            "token conservation including external donations and burns"
        );
    }
    /// The door mint alone locates its Door: room, door_nonce and program from the
    /// mint's metadata derive the Door PDA, and that Door names this mint back.
    fn audit_door_metadata(&self, door: Pubkey, d: &Door) {
        let account = self.svm.get_account(&d.mint).unwrap();
        let m = StateWithExtensions::<Mint>::unpack(&account.data).unwrap();
        let md = m
            .get_variable_len_extension::<spl_token_metadata_interface::state::TokenMetadata>()
            .unwrap();
        let expected = vec![
            ("room".to_string(), d.room.to_string()),
            ("door".to_string(), d.index.to_string()),
            ("door_nonce".to_string(), d.nonce.to_string()),
            ("program".to_string(), ID.to_string()),
        ];
        assert_eq!(md.additional_metadata, expected);
        // Size and rent: the account is exactly base mint + TLV headers + this metadata,
        // the formula research/doors_into_one_room/scripts/account_sizes.py uses.
        let value = 64
            + 12
            + md.name.len()
            + md.symbol.len()
            + md.uri.len()
            + 4
            + expected
                .iter()
                .map(|(k, v)| 8 + k.len() + v.len())
                .sum::<usize>();
        assert_eq!(account.data.len(), 165 + 1 + (4 + 64) + 4 + value);
        assert!(
            account.lamports
                >= self
                    .svm
                    .minimum_balance_for_rent_exemption(account.data.len())
        );
        let get = |k: &str| {
            md.additional_metadata
                .iter()
                .find(|(key, _)| key == k)
                .unwrap()
                .1
                .clone()
        };
        let room: Pubkey = get("room").parse().unwrap();
        let nonce: u64 = get("door_nonce").parse().unwrap();
        let program: Pubkey = get("program").parse().unwrap();
        let derived =
            Pubkey::find_program_address(&[b"door", room.as_ref(), &nonce.to_le_bytes()], &program)
                .0;
        assert_eq!(derived, door);
        let back =
            Door::try_deserialize(&mut &self.svm.get_account(&derived).unwrap().data[..]).unwrap();
        assert_eq!(back.mint, d.mint);
    }
    fn time(&mut self, seconds: i64) {
        let mut c = self.svm.get_sysvar::<Clock>();
        c.unix_timestamp += seconds;
        self.svm.set_sysvar(&c);
    }
}

#[test]
fn creates_exact_layouts_immutable_mints_and_signed_optional_first_buy() {
    let mut f = Fixture::empty(0);
    let mut l = launch("First room");
    l.first_buy_lamports = 1_010_000_000;
    f.create(l, None);
    assert_eq!(f.svm.get_account(&f.cfg).unwrap().data.len(), Config::LEN);
    assert_eq!(f.r().reserve, 1_000_000_000);
    assert!(f.d(0).backing > 0);
    assert_eq!(f.r().founder, f.user.pubkey());
    assert_eq!(f.r().founder_share_bps, 0);
    assert_eq!(f.r().founder_accrued, 0);
    let mint = f.svm.get_account(&f.r().room_mint).unwrap();
    assert_eq!(
        StateWithExtensions::<Mint>::unpack(&mint.data)
            .unwrap()
            .base
            .supply,
        U
    );
    let mut l = launch("Another face");
    l.first_buy_lamports = 101_000_000;
    f.open(l);
    assert!(f.d(1).backing > 0);
}

#[test]
fn record_actual_launch_account_sizes_for_matcher_funding_check() {
    let mut f = Fixture::empty(0);
    let mut l = launch("Funding room");
    l.first_buy_lamports = 1_010_000_000;
    let ix = f.create_ix(l.clone(), None);
    let keys: std::collections::BTreeSet<_> = ix
        .accounts
        .iter()
        .filter(|a| a.is_writable && f.svm.get_account(&a.pubkey).is_none())
        .map(|a| a.pubkey)
        .collect();
    f.create(l.clone(), None);
    let mut sizes: Vec<_> = keys
        .iter()
        .map(|key| f.svm.get_account(key).unwrap().data.len())
        .collect();
    sizes.sort();
    let out = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../verification/launch_rent_accounts.json");
    std::fs::write(
        out,
        serde_json::to_string_pretty(&json!({
            "source":"actual accounts created by compiled SBF in LiteSVM",
            "name":l.name,"symbol":l.symbol,"uri":l.uri,"first_buy":l.first_buy_lamports,
            "room":f.room.to_string(),"program":ID.to_string(),"sizes":sizes,
        }))
        .unwrap()
            + "\n",
    )
    .unwrap();
}

#[test]
fn prefunding_all_launch_pdas_cannot_block_an_atomic_first_buy() {
    let mut f = Fixture::empty(0);
    let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
    settings.room_fee_lamports = 7;
    settings.door_fee_lamports = 11;
    f.send(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        "update_config",
    );
    let mut l = launch("Prefunded room");
    l.max_fee_lamports = 18;
    l.first_buy_lamports = 1_010_000_000;
    let ix = f.create_ix(l.clone(), None);
    let rent = f.svm.minimum_balance_for_rent_exemption(0);
    // Anyone can fund a PDA before its program allocates it. Use real
    // System transfers, including the user's future canonical ATA.
    for account in &ix.accounts {
        if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
            f.svm.airdrop(&account.pubkey, rent).unwrap();
            assert_eq!(f.svm.get_account(&account.pubkey).unwrap().lamports, rent);
        }
    }
    f.create(l, None);
    assert_eq!(f.r().reserve, 1_000_000_000);
    let mut l = launch("Prefunded door");
    l.max_fee_lamports = 11;
    l.first_buy_lamports = 101_000_000;
    let ix = f.open_ix(l.clone(), None);
    for account in &ix.accounts {
        if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
            f.svm.airdrop(&account.pubkey, rent).unwrap();
        }
    }
    f.open(l);
    assert!(f.d(1).backing > 0);
}

#[test]
fn maximum_metadata_creation_executes_in_a_packet_sized_v0_transaction() {
    use solana_address_lookup_table_interface::instruction::{
        create_lookup_table, extend_lookup_table,
    };
    use solana_message::{v0, AddressLookupTableAccount, VersionedMessage};
    use solana_transaction::versioned::VersionedTransaction;
    let mut f = Fixture::empty(0);
    let mut l = launch(&"x".repeat(32));
    l.symbol = "Y".repeat(10);
    l.uri = "u".repeat(200);
    l.first_buy_lamports = 1_010_000_000;
    l.min_tokens_out = 1;
    let main = f.create_ix(l, None);
    let instructions = [
        ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
        main.clone(),
    ];
    let hash = f.svm.latest_blockhash();
    let legacy = Transaction::new(
        &[&f.user, &f.matcher],
        Message::new(&instructions, Some(&f.user.pubkey())),
        hash,
    );
    let legacy_bytes = 1 + 64 * legacy.signatures.len() + legacy.message_data().len();
    assert!(
        legacy_bytes > 1232,
        "fixture must exercise the packet-size boundary"
    );
    let slot = f.svm.get_sysvar::<Clock>().slot;
    let (create, table) = create_lookup_table(f.user.pubkey(), f.user.pubkey(), slot);
    f.send(create, false, "create_lookup_table");
    let addresses: Vec<Pubkey> = main.accounts.iter().map(|a| a.pubkey).collect();
    f.send(
        extend_lookup_table(
            table,
            f.user.pubkey(),
            Some(f.user.pubkey()),
            addresses.clone(),
        ),
        false,
        "extend_lookup_table",
    );
    f.svm.warp_to_slot(slot + 1);
    let message = v0::Message::try_compile(
        &f.user.pubkey(),
        &instructions,
        &[AddressLookupTableAccount {
            key: table,
            addresses,
        }],
        hash,
    )
    .unwrap();
    let tx = VersionedTransaction::try_new(VersionedMessage::V0(message), &[&f.user, &f.matcher])
        .unwrap();
    let v0_bytes = 1 + 64 * tx.signatures.len() + tx.message.serialize().len();
    assert!(v0_bytes <= 1232);
    let result = f
        .svm
        .send_transaction(tx)
        .unwrap_or_else(|e| panic!("maximum-metadata v0 create: {e:#?}"));
    f.doors.push(DoorKeys::new(f.room, 0, f.user.pubkey()));
    f.audit();
    // Measure maximum-length room/door metadata as well as larger curve
    // positions and the capped crossing path. The random run uses short URIs.
    let mut face = launch(&"x".repeat(32));
    face.symbol = "Y".repeat(10);
    face.uri = "u".repeat(200);
    f.open(face);
    f.trade(Some(0), true, 70_700_000_000);
    f.trade(Some(1), true, 1_010_000);
    f.trade(Some(0), false, 1);
    let amount = f.balance(f.doors[0].user) / 2;
    f.convert(0, 1, amount);
    f.trade(Some(1), false, amount / 2);
    f.make_ata(f.r().room_mint, spl_token_2022_interface::ID);
    f.trade(None, true, 1_010_000);
    let amount = f.balance(ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    ));
    f.trade(None, false, amount / 2);
    f.trade(Some(0), true, u64::MAX / 100);
    assert_eq!(f.r().status, 1);
    f.convert(0, 1, 1);
    let output = json!({"packet_limit":1232,"legacy_bytes":legacy_bytes,"v0_bytes":v0_bytes,"metadata_bytes":{"name":32,"symbol":10,"uri":200},"first_buy_lamports":1_010_000_000u64,"transaction_cu":result.compute_units_consumed,"edge_cu_samples":f.cus});
    let out = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification/packets.json");
    std::fs::write(out, serde_json::to_string_pretty(&output).unwrap() + "\n").unwrap();
}

#[test]
fn trade_event_reports_the_exact_counter_based_price_and_position() {
    use anchor_lang::{AnchorDeserialize, Discriminator};
    use base64::{engine::general_purpose::STANDARD, Engine};
    let mut f = Fixture::new(0);
    let meta = f.checked(
        f.trade_ix(Some(0), true, 1_010_000_000, 0),
        false,
        "buy_door",
    );
    f.audit();
    let bytes = meta
        .logs
        .iter()
        .filter_map(|line| line.strip_prefix("Program data: "))
        .filter_map(|text| STANDARD.decode(text).ok())
        .find(|data| data.starts_with(doors_v1::Trade::DISCRIMINATOR))
        .expect("Trade event");
    let event = doors_v1::Trade::try_from_slice(&bytes[8..]).unwrap();
    let r = f.r();
    assert_eq!(event.sold_after, r.sold);
    assert_eq!(event.reserve, r.reserve);
    assert_eq!(
        event.price_after.numerator,
        (r.v_sol_lamports as u128) * (r.v_tok as u128)
    );
    assert_eq!(
        event.price_after.denominator,
        ((r.v_tok - r.sold) as u128) * ((r.v_tok - r.sold) as u128)
    );
}

#[test]
fn substituted_trade_accounts_and_same_door_conversion_are_rejected_atomically() {
    let mut f = Fixture::new(0);
    f.open(launch("Second face"));
    f.trade(Some(0), true, 1_010_000_000);
    let c = f.core();
    let x = f.doors[0].clone();
    let y = f.doors[1].clone();
    for (valid, substituted) in [
        (c.reserve, c.fees),
        (c.fees, c.reserve),
        (c.room_mint, y.mint),
        (c.room_vault, x.backing),
        (c.retired, c.room_vault),
        (x.door, y.door),
        (x.mint, y.mint),
        (x.vault, y.vault),
        (x.backing, y.backing),
        (x.user, y.user),
        (spl_token_2022_interface::ID, spl_token_interface::ID),
    ] {
        for buy in [true, false] {
            let mut instruction = f.trade_ix(Some(0), buy, 101, 0);
            for meta in &mut instruction.accounts {
                if meta.pubkey == valid {
                    meta.pubkey = substituted;
                }
            }
            f.fail(instruction, false);
            f.audit();
        }
    }
    f.fail(f.convert_ix(0, 0, 1), false);
    f.audit();
}

#[test]
fn independent_holders_share_backing_without_access_to_each_others_fees() {
    let mut f = Fixture::new(0);
    f.open(launch("Second face"));
    f.trade(Some(0), true, 1_010_000_000);
    let first_ata = f.doors[0].user;
    let first_balance = f.balance(first_ata);
    let first_holder = std::mem::replace(&mut f.user, Keypair::new_from_array([33; 32]));
    f.svm.airdrop(&f.user.pubkey(), 10_000_000_000).unwrap();
    for i in 0..f.doors.len() {
        let mint = f.doors[i].mint;
        f.doors[i].user = ata(f.user.pubkey(), mint, spl_token_2022_interface::ID);
        f.make_ata(mint, spl_token_2022_interface::ID);
    }
    f.make_ata(
        spl_token_interface::native_mint::ID,
        spl_token_interface::ID,
    );
    f.trade(Some(1), true, 1_010_000_000);
    let half = f.balance(f.doors[1].user) / 2;
    f.convert(1, 0, half);
    assert_eq!(f.balance(first_ata), first_balance);
    f.fail(f.claim_ix(0, 0, first_holder.pubkey()), false);
    f.fail(f.claim_ix(1, 0, first_holder.pubkey()), false);
    for i in 0..f.doors.len() {
        let amount = f.balance(f.doors[i].user);
        f.trade(Some(i), false, amount);
    }
    assert_eq!(f.balance(first_ata), first_balance);
    assert_eq!(f.r().sold, first_balance);
    f.user = first_holder;
    for d in &mut f.doors {
        d.user = ata(f.user.pubkey(), d.mint, spl_token_2022_interface::ID);
    }
    f.trade(Some(0), false, first_balance);
    assert_eq!(f.r().sold, 0);
    assert_eq!(f.d(0).backing, 0);
    assert_eq!(f.d(1).backing, 0);
    f.claim(0, 0);
    f.claim(0, 1);
}
#[test]
fn signatures_cover_the_entire_message_and_nonce() {
    let mut f = Fixture::empty(0);
    let instruction = f.create_ix(launch("First room"), None);
    let mut unsigned =
        Transaction::new_unsigned(Message::new(&[instruction.clone()], Some(&f.user.pubkey())));
    unsigned.partial_sign(&[&f.user], f.svm.latest_blockhash());
    assert!(f.svm.send_transaction(unsigned).is_err());
    let mut changed = Transaction::new(
        &[&f.user, &f.matcher],
        Message::new(&[instruction.clone()], Some(&f.user.pubkey())),
        f.svm.latest_blockhash(),
    );
    changed.message.instructions[0].data[8] ^= 1;
    assert!(f.svm.send_transaction(changed).is_err());
    let mut changed = Transaction::new(
        &[&f.user, &f.matcher],
        Message::new(&[instruction], Some(&f.user.pubkey())),
        f.svm.latest_blockhash(),
    );
    changed.message.instructions[0].data[25] ^= 1;
    assert!(f.svm.send_transaction(changed).is_err());
    assert!(f.svm.get_account(&f.room).is_none());
    f.create(launch("First room"), None);
    let open = f.open_ix(launch("Another face"), None);
    let mut changed = Transaction::new(
        &[&f.user, &f.matcher],
        Message::new(&[open], Some(&f.user.pubkey())),
        f.svm.latest_blockhash(),
    );
    changed.message.instructions[0].accounts[3] = changed.message.instructions[0].accounts[2];
    assert!(f.svm.send_transaction(changed).is_err());
    f.fail(f.create_ix(launch("First room"), None), true); // occupied random nonce cannot overwrite a room
}

#[test]
fn a_propagated_signer_cannot_authorize_reinterpreted_cpi_launch_data() {
    let mut f = Fixture::empty(0);
    let proxy = Pubkey::new_from_array([29; 32]);
    let elf = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../target/deploy/launch_proxy.so");
    f.svm
        .add_program(
            proxy,
            &std::fs::read(elf).expect("build the test-only launch proxy"),
        )
        .unwrap();
    let original = f.create_ix(launch("First room"), None);
    let mut metas = vec![AccountMeta::new_readonly(ID, false)];
    metas.extend(original.accounts);
    let instruction = Instruction {
        program_id: proxy,
        accounts: metas,
        data: original.data,
    };
    let tx = Transaction::new(
        &[&f.user, &f.matcher],
        Message::new(&[instruction], Some(&f.user.pubkey())),
        f.svm.latest_blockhash(),
    );
    let err = f.svm.send_transaction(tx).unwrap_err();
    assert!(
        err.meta.logs.iter().any(|line| line.contains("LaunchCpi")),
        "{err:#?}"
    );
    assert!(f.svm.get_account(&f.room).is_none());
    assert!(f
        .svm
        .get_account(&p(&[b"reserve", f.room.as_ref()]))
        .is_none());
}
#[test]
fn buy_sell_convert_full_redemption_and_zero_balance_edges() {
    let mut f = Fixture::new(0);
    f.open(launch("Second"));
    f.fail(f.convert_ix(0, 1, 1), false);
    f.fail(f.convert_ix(0, 1, 0), false);
    f.trade(Some(0), true, 1_010_000_000);
    let n = f.balance(f.doors[0].user);
    f.convert(0, 1, n);
    assert_eq!(f.balance(f.doors[0].user), 0);
    f.trade(Some(1), false, n);
    assert_eq!(f.r().sold, 0);
    assert_eq!(f.d(0).backing, 0);
    assert_eq!(f.d(1).backing, 0);
    let expected_room_tokens = n;
    f.trade(None, true, 1_010_000_000);
    let n = f.balance(ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    ));
    assert_eq!(
        n, expected_room_tokens,
        "P1: identical state/input quotes identically across routes"
    );
    f.trade(None, false, n);
    assert_eq!(f.r().sold, 0);
    f.fail(f.trade_ix(Some(0), true, 100_000, u64::MAX), false);
    f.fail(f.trade_ix(None, false, 1, 0), false);
}
#[test]
fn crossing_buy_caps_but_completion_preserves_door_and_room_exits() {
    let mut f = Fixture::new(0);
    f.trade(Some(0), true, 101); // integer dust/slack
    let before = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    let r = f.r();
    let n = r.graduation_trigger_lamports - r.reserve;
    let fee = doors_v1::math::ratio(n, r.fee_bps, true).unwrap();
    f.trade(Some(0), true, u64::MAX / 100);
    let r = f.r();
    assert_eq!(r.reserve, r.graduation_trigger_lamports);
    assert_eq!(r.status, 1);
    assert_eq!(
        before - f.svm.get_account(&f.user.pubkey()).unwrap().lamports,
        n + fee + 5000
    );
    f.fail(f.trade_ix(Some(0), true, 101, 0), false);
    f.open(launch("Complete door"));
    let half = f.balance(f.doors[0].user) / 2;
    f.convert(0, 1, half);
    f.trade(Some(1), false, half);
    assert_eq!(f.r().status, 0);
    f.trade(None, true, u64::MAX / 100);
    assert_eq!(f.r().status, 1);
    let room_tokens = f.balance(ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    ));
    f.trade(None, false, room_tokens);
    f.trade(Some(0), false, f.balance(f.doors[0].user));
    assert_eq!(f.r().sold, 0);
    assert_eq!(f.r().status, 0);
    f.trade(Some(0), true, 101);
    f.claim(0, 0);
    f.claim(1, 0);
    f.claim(2, 0);
}
#[test]
fn founder_split_snapshot_claims_and_admin_bounds() {
    let mut f = Fixture::new(1000);
    f.trade(Some(0), true, 1_010_000_000);
    assert_eq!(f.d(0).accrued_sol, 6_000_000);
    assert_eq!(f.r().founder_accrued, 1_000_000);
    assert_eq!(f.r().protocol_accrued_sol, 3_000_000);
    let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
    s.founder_share_bps = 0;
    s.graduation_trigger_lamports += 1000;
    f.checked(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings: s.clone(),
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        "update_config",
    );
    assert_eq!(f.r().founder_share_bps, 1000);
    assert_ne!(
        f.r().graduation_trigger_lamports,
        s.graduation_trigger_lamports
    );
    s.founder_share_bps = 5000;
    f.fail(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings: s,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
    );
    let mut forged = f.claim_ix(1, 0, f.user.pubkey());
    forged.accounts[0] = AccountMeta::new_readonly(f.matcher.pubkey(), true);
    f.fail(forged, true);
    for k in 0..3 {
        f.claim(k, 0);
        f.claim(k, 0);
    }
    assert_eq!(f.d(0).claimed_sol, 6_000_000);
    assert_eq!(f.r().founder_accrued, 0);
    assert_eq!(f.r().protocol_accrued_sol, 0);
}
#[test]
fn retirement_is_capped_and_does_not_retire_surplus() {
    let mut f = Fixture::new(0);
    f.trade(None, true, 1_010_000_000);
    let before = f.r();
    assert_eq!(before.pending_reserve_sol, 6_000_000);
    f.retire();
    assert_eq!(f.r().reserve, before.reserve + before.pending_reserve_sol);
    assert!(f.r().retired > 0);
    assert_eq!(f.r().pending_reserve_sol, 0);
    f.retire();
    // Change the *initial fixture* trigger to exercise a pending amount beyond the cap.
    let mut g = Fixture::empty(0);
    let mut s = defaults(g.matcher.pubkey(), g.user.pubkey());
    s.graduation_trigger_lamports = 85_018_013_680;
    g.send(
        instr(
            a::UpdateConfig {
                admin: g.user.pubkey(),
                config: g.cfg,
            },
            ix::UpdateConfig {
                settings: s,
                new_admin: g.user.pubkey(),
            },
        ),
        false,
        "update_config",
    );
    g.create(launch("First room"), None);
    g.trade(None, true, 85_860_000_000);
    let before = g.r();
    assert!(before.reserve < before.graduation_trigger_lamports);
    assert!(before.pending_reserve_sol > before.graduation_trigger_lamports - before.reserve);
    g.retire();
    assert_eq!(g.r().status, 1);
    assert_eq!(g.r().reserve, g.r().graduation_trigger_lamports);
    assert!(g.r().pending_reserve_sol > 0);
    let held = g.balance(ata(
        g.user.pubkey(),
        g.r().room_mint,
        spl_token_2022_interface::ID,
    ));
    g.trade(None, false, held);
    assert_eq!(g.r().status, 0);
    assert_eq!(g.r().sold, g.r().retired);
    g.trade(Some(0), true, 1_010_000);
}
#[test]
fn wsol_fee_plumbing_claims_only_accounted_fees_and_leaves_donations_locked() {
    let mut f = Fixture::new(1000);
    // Explicit future-phase fee fixture: v1 itself never accrues pool WSOL fees.
    // Transfers and claims below still execute real classic-SPL CPIs in SBF.
    let rk = f.room;
    let dk = f.doors[0].door;
    let mut r = f.r();
    let mut d = f.d(0);
    r.founder_accrued_wsol = 100;
    r.protocol_accrued_wsol = 300;
    r.pending_reserve_wsol = 50;
    d.accrued_wsol = 600;
    let mut account = f.svm.get_account(&rk).unwrap();
    r.try_serialize(&mut &mut account.data[..]).unwrap();
    f.svm.set_account(rk, account).unwrap();
    let mut account = f.svm.get_account(&dk).unwrap();
    d.try_serialize(&mut &mut account.data[..]).unwrap();
    f.svm.set_account(dk, account).unwrap();
    f.send(
        solana_system_interface::instruction::transfer(&f.user.pubkey(), &r.fee_wsol, 1127),
        false,
        "fixture_wsol_funding",
    );
    f.send(
        spl_token_interface::instruction::sync_native(&spl_token_interface::ID, &r.fee_wsol)
            .unwrap(),
        false,
        "fixture_wsol_sync",
    );
    f.audit();
    let reserve = f.r().reserve;
    for kind in 0..3 {
        f.claim(kind, 0);
        f.claim(kind, 0);
    }
    assert_eq!(f.r().reserve, reserve);
    assert_eq!(f.balance(r.fee_wsol), 127); // pending 50 + locked donation 77
    assert_eq!(
        f.balance(ata(
            f.user.pubkey(),
            spl_token_interface::native_mint::ID,
            spl_token_interface::ID
        )),
        1000
    );
    assert_eq!(f.d(0).claimed_wsol, 600);
    assert_eq!(f.r().pending_reserve_wsol, 50);
}

#[test]
fn mature_gate_is_the_same_for_routing_and_release() {
    let mut f = Fixture::new(0);
    f.trade(Some(0), true, 5_050_000_000);
    f.time(3600);
    let r = f.r();
    let c = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    let now = f.svm.get_sysvar::<Clock>().unix_timestamp;
    assert!(r.live(&c, now).unwrap());
    let slug = p(&[b"slug", &r.identity]);
    let release = instr(
        a::ReleaseSlug {
            caller: f.user.pubkey(),
            config: f.cfg,
            room: f.room,
            slug,
        },
        ix::ReleaseSlug {},
    );
    f.fail(release.clone(), false);
    f.open(launch("Mature live face"));
    f.time(21601);
    assert!(!f
        .r()
        .live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    f.fail(f.open_ix(launch("Stale target"), None), true);
    f.checked(release, false, "release_slug");
}

#[test]
fn buy_fees_do_not_make_a_below_threshold_room_live() {
    let mut f = Fixture::new(0);
    let c = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    // Wallet spend equals V_min, but the curve receives less after fees.
    f.trade(Some(0), true, c.live_min_volume_lamports);
    f.time(c.live_new_seconds as i64);
    let r = f.r();
    assert!(r.reserve >= c.live_min_reserve_lamports);
    assert!(r.volume_gross < c.live_min_volume_lamports as u128);
    assert_eq!(r.volume_gross, r.reserve as u128);
    assert_eq!(f.d(0).buy_volume, r.volume_gross);
    assert!(!r
        .live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    f.fail(f.open_ix(launch("Below volume floor"), None), true);
    // At the true fee-base threshold routing becomes eligible again.
    f.trade(Some(0), true, 101_000_000);
    assert!(f
        .r()
        .live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    f.open(launch("Above volume floor"));
}

#[test]
fn direct_donations_and_holder_burns_preserve_coverage_and_quotes() {
    let mut f = Fixture::new(0);
    f.trade(Some(0), true, 1_010_000_000);
    f.trade(None, true, 1_010_000_000);
    let r = f.r();
    let d = f.d(0);
    let keys = f.doors[0].clone();
    for (mint, source, dest) in [
        (keys.mint, keys.user, keys.vault),
        (
            r.room_mint,
            ata(f.user.pubkey(), r.room_mint, spl_token_2022_interface::ID),
            r.room_vault,
        ),
        (
            r.room_mint,
            ata(f.user.pubkey(), r.room_mint, spl_token_2022_interface::ID),
            keys.backing,
        ),
        (
            r.room_mint,
            ata(f.user.pubkey(), r.room_mint, spl_token_2022_interface::ID),
            r.retired_vault,
        ),
    ] {
        f.send(
            spl_token_2022_interface::instruction::transfer_checked(
                &spl_token_2022_interface::ID,
                &source,
                &mint,
                &dest,
                &f.user.pubkey(),
                &[],
                1,
                6,
            )
            .unwrap(),
            false,
            "external_donation",
        );
    }
    f.send(
        spl_token_2022_interface::instruction::burn_checked(
            &spl_token_2022_interface::ID,
            &keys.user,
            &keys.mint,
            &f.user.pubkey(),
            &[],
            1,
            6,
        )
        .unwrap(),
        false,
        "external_burn",
    );
    assert_eq!(f.r().sold, r.sold);
    assert_eq!(f.d(0).backing, d.backing);
    f.audit();
    let reserve = p(&[b"reserve", f.room.as_ref()]);
    let fees = p(&[b"fees", f.room.as_ref()]);
    for key in [reserve, fees] {
        f.send(
            solana_system_interface::instruction::transfer(&f.user.pubkey(), &key, 777),
            false,
            "native_donation",
        );
    }
    let mut before = f.r();
    // A buy first settles pending room-route fees (capped at the trigger), then
    // advances by its own net input. Donations change neither step.
    let pending = before
        .pending_reserve_sol
        .min(before.graduation_trigger_lamports - before.reserve);
    assert!(
        pending > 0,
        "the room-token buy above must leave pending fees"
    );
    before.sold = before.advance(pending).unwrap();
    before.reserve += pending;
    let q = before.advance(1_000_000).unwrap();
    f.trade(Some(0), true, 1_010_000);
    assert_eq!(f.r().sold, q);
    let tokens = f.balance(keys.user);
    f.trade(Some(0), false, tokens);
    assert_eq!(f.balance(keys.vault) - (U - f.d(0).backing), 1);
    let locked = f.balance(keys.backing) - f.d(0).backing;
    f.claim(0, 0);
    f.claim(1, 0);
    f.claim(2, 0);
    assert_eq!(f.balance(keys.backing) - f.d(0).backing, locked);
}
#[test]
fn fee_recipient_rotation_and_pause() {
    let mut f = Fixture::new(0);
    f.trade(Some(0), true, 101000);
    let next = f.matcher.pubkey();
    let d = f.doors[0].clone();
    let set = instr(
        a::SetRecipient {
            authority: f.user.pubkey(),
            core: f.core(),
            door: d.door,
            door_mint: d.mint,
            door_vault: d.vault,
            backing: d.backing,
        },
        ix::SetFeeRecipient {
            new_recipient: next,
        },
    );
    f.checked(set, false, "set_fee_recipient");
    assert_eq!(f.d(0).fee_recipient, next);
    f.fail(f.claim_ix(0, 0, f.user.pubkey()), false);
    let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
    s.paused = true;
    f.checked(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings: s,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        "update_config",
    );
    f.fail_error(f.trade_ix(Some(0), true, 101, 0), false, Some("Paused"));
    f.fail_error(f.trade_ix(None, true, 101_000, 0), false, Some("Paused"));
    f.fail_error(f.open_ix(launch("Paused"), None), true, Some("Paused"));
    f.claim(1, 0);
    f.claim(2, 0);
}

// Pause must not trap holders: while paused, door sells, room sells and conversions still
// execute with every invariant asserted (`checked` + `audit`), while buys, launches and
// fee settlement stay blocked. Unpausing restores buys.
#[test]
fn pause_blocks_new_positions_but_holders_can_still_exit() {
    let mut f = Fixture::new(0);
    f.open(launch("Second face"));
    f.trade(Some(0), true, 50_000_000);
    f.trade(Some(1), true, 20_000_000);
    f.trade(None, true, 10_000_000);
    assert!(f.r().pending_reserve_sol > 0);
    let set_paused = |f: &mut Fixture, paused: bool| {
        let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
        s.paused = paused;
        f.checked(
            instr(
                a::UpdateConfig {
                    admin: f.user.pubkey(),
                    config: f.cfg,
                },
                ix::UpdateConfig {
                    settings: s,
                    new_admin: f.user.pubkey(),
                },
            ),
            false,
            "update_config",
        );
    };
    set_paused(&mut f, true);
    // Blocked: every way to take a new position or create anything.
    f.fail_error(
        f.trade_ix(Some(0), true, 1_010_000, 0),
        false,
        Some("Paused"),
    );
    f.fail_error(f.trade_ix(None, true, 1_010_000, 0), false, Some("Paused"));
    f.fail_error(f.open_ix(launch("Paused door"), None), true, Some("Paused"));
    let c = f.core();
    let output = c.retired;
    f.fail_error(
        instr(
            a::Retire {
                core: c,
                retired_output: output,
                token_program: spl_token_2022_interface::ID,
            },
            ix::RetirePending {},
        ),
        false,
        Some("Paused"),
    );
    // Open: convert part of door 0 into door 1, then exit every position completely.
    let held0 = f.balance(f.doors[0].user);
    f.convert(0, 1, held0 / 2);
    let room_ata = ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    );
    for door in [Some(0), Some(1), None] {
        let held = match door {
            Some(i) => f.balance(f.doors[i].user),
            None => f.balance(room_ata),
        };
        assert!(held > 0);
        f.trade(door, false, held);
    }
    assert_eq!(f.balance(f.doors[0].user), 0);
    assert_eq!(f.balance(f.doors[1].user), 0);
    assert_eq!(f.balance(room_ata), 0);
    assert_eq!(f.r().sold, f.r().retired);
    // Claims were never gated.
    f.claim(0, 0);
    set_paused(&mut f, false);
    f.trade(Some(1), true, 1_010_000);
}
#[test]
fn liveness_boundary_release_takeover_and_exact_floor() {
    let mut f = Fixture::new(0);
    let identity = f.r().identity;
    let slug = p(&[b"slug", &identity]);
    let release = |f: &Fixture| {
        instr(
            a::ReleaseSlug {
                caller: f.user.pubkey(),
                config: f.cfg,
                room: f.room,
                slug,
            },
            ix::ReleaseSlug {},
        )
    };
    f.fail(release(&f), false);
    f.time(3599);
    f.fail(release(&f), false);
    f.time(1);
    f.fail(f.open_ix(launch("Dead target"), None), true);
    f.checked(release(&f), false, "release_slug");
    assert!(f.svm.get_account(&slug).is_none());
    // A dead room keeps its immutable creation timestamp and may still trade by id.
    let created = f.r().created_at;
    f.trade(Some(0), true, 101000);
    assert_eq!(f.r().created_at, created);
    let old = f.room;
    f.rid = 0x27c4_8931_719f_ea52;
    f.room = p(&[b"room", &f.rid.to_le_bytes()]);
    f.doors.clear();
    f.create(launch("First room"), None);
    assert_ne!(f.room, old);
    // A second room cannot steal a live exact identity, even with a matcher signature.
    let live = f.room;
    f.rid = 0xab37_c421_4d82_9e15;
    f.room = p(&[b"room", &f.rid.to_le_bytes()]);
    f.doors.clear();
    f.fail(f.create_ix(launch("First room"), Some(live)), true);
    f.time(3600);
    f.create(launch("First room"), Some(live));
    assert_eq!(f.r().created_at, created + 7200);
}
#[test]
fn fold_and_integer_math_match_reference_vectors() {
    use doors_v1::{math::*, state::fold};
    assert_eq!(fold(b"rn-vv 0134578"), b"MWOIEASTB");
    assert_eq!(fold("Ã©rn-vv 0".as_bytes()), "Ã©RNVVO".as_bytes());
    let vs = 30_000_852_995;
    let vt = 1_073_025_606_000_000;
    let mut seed = 0x381f_b84b_b9e7_2e01u64;
    for _ in 0..10000 {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        let n = seed % 85_018_013_681;
        let q = inverse(vs, vt, n).unwrap();
        assert!(reserve(vs, vt, q).unwrap() <= n);
        assert!(reserve(vs, vt, q + 1).unwrap() > n);
    }
}
#[test]
fn mixed_10000_sbf_operations_and_cu_report() {
    let mut f = Fixture::new(0);
    f.open(launch("Second face"));
    f.open(launch("Third face"));
    let mut rng = 0x8c65_13ab_72ef_d501u64;
    let mut counts = BTreeMap::<String, u64>::new();
    for step in 0..10000 {
        rng ^= rng << 13;
        rng ^= rng >> 7;
        rng ^= rng << 17;
        let i = (rng as usize / 16) % 3;
        let op = rng % 12;
        let label = match op {
            0..=3 => {
                f.trade(Some(i), true, 101000 + (rng % 900000));
                "buy_door"
            }
            4 => {
                f.trade(None, true, 101000 + (rng % 900000));
                "buy_room"
            }
            5 | 6 => {
                let n = f.balance(f.doors[i].user) / 2;
                if n > 0 {
                    f.trade(Some(i), false, n);
                } else {
                    f.trade(Some(i), true, 101000);
                }
                "sell_door_or_seed"
            }
            7 => {
                let key = ata(
                    f.user.pubkey(),
                    f.r().room_mint,
                    spl_token_2022_interface::ID,
                );
                let n = f.balance(key) / 2;
                if n > 0 {
                    f.trade(None, false, n);
                } else {
                    f.trade(None, true, 101000);
                }
                "sell_room_or_seed"
            }
            8 => {
                let n = f.balance(f.doors[i].user) / 2;
                if n > 0 {
                    f.convert(i, (i + 1) % 3, n);
                } else {
                    f.trade(Some(i), true, 101000);
                }
                "convert_or_seed"
            }
            9 => {
                f.retire();
                "retire_pending"
            }
            10 => {
                f.claim(0, i);
                "claim_door_fees"
            }
            _ => {
                f.claim(1, 0);
                f.claim(2, 0);
                "claim_founder_and_protocol"
            }
        };
        *counts.entry(label.into()).or_default() += 1;
        f.audit();
        if step % 1000 == 0 {
            println!("mixed SBF operations checked: {step}");
        }
    }
    // Measure the requested open_door at the maximum permitted metadata lengths,
    // separately from the smaller test-face launches above.
    let mut max = launch(&"x".repeat(32));
    max.symbol = "Y".repeat(10);
    max.uri = "u".repeat(200);
    f.open(max);
    let summary:BTreeMap<String,Value>=f.cus.iter().map(|(k,v)|(k.clone(),json!({"count":v.len(),"min":v.iter().min(),"max":v.iter().max(),"sum":v.iter().sum::<u64>(),"samples":v}))).collect();
    let output = json!({"kind":"executed compiled Anchor SBF in LiteSVM with real SPL CPIs", "property_iterations":10000,"executed_transactions":f.operations,"seed":"8c6513ab72efd501","operation_counts":counts,"cu":summary});
    let out = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification");
    std::fs::create_dir_all(&out).unwrap();
    std::fs::write(
        out.join("svm_report.json"),
        serde_json::to_string_pretty(&output).unwrap() + "\n",
    )
    .unwrap();
    println!("CU_REPORT property_iterations=10000 executed_transactions={} max_door_buy={} max_door_sell={} max_convert={} max_open_door={}",f.operations,f.cus["buy_door"].iter().max().unwrap(),f.cus["sell_door"].iter().max().unwrap(),f.cus["convert"].iter().max().unwrap(),f.cus["open_door"].iter().max().unwrap());
}

// Regression tests for the audit findings. Every instruction executes SBF.
fn audit_settings(f: &mut Fixture, settings: Settings) {
    f.send(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        "audit_config",
    );
}

#[test]
fn config_rejects_a_curve_with_no_purchasable_base_unit() {
    let mut f = Fixture::empty(0);
    let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
    s.v_tok = U + 1;
    s.v_sol_lamports = 2 * (U + 1);
    s.r_star_lamports = 1;
    s.graduation_trigger_lamports = 1;
    f.fail_error(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings: s,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        Some("BadConfig"),
    );
    f.create(launch("Valid config preserved"), None);
    f.trade(Some(0), true, 101);
}

#[test]
fn large_virtual_reserve_quotes_and_redemptions_do_not_overflow() {
    let mut f = Fixture::empty(0);
    let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
    s.v_tok = U + 1;
    s.v_sol_lamports = u64::MAX;
    s.r_star_lamports = 1;
    s.graduation_trigger_lamports = 1_000_000;
    audit_settings(&mut f, s);
    f.create(launch("Intermediate overflow"), None);
    let r = f.r();
    let k = (r.v_sol_lamports as u128) * (r.v_tok as u128);
    let exact = k / ((r.v_tok - 1) as u128) - (r.v_sol_lamports as u128);
    assert!(exact > 0 && exact <= u64::MAX as u128);
    assert_eq!(r.curve(1).unwrap() as u128, exact);
    f.trade(Some(0), true, 101_000);
    let held = f.balance(f.doors[0].user);
    assert!(held > 0);
    let slack = f.r().reserve - f.r().curve(held).unwrap();
    f.trade(Some(0), false, held);
    assert_eq!(f.r().sold, 0);
    assert_eq!(f.r().reserve, slack);
}

#[test]
fn curve_quotes_match_the_exact_reference_at_integer_boundaries() {
    for vs in [1, 30_000_000_000, u64::MAX / 2, u64::MAX] {
        for vt in [U + 1, 2 * U, u64::MAX] {
            for q in [0, 1, U / 2, U - 1, U] {
                let exact = (vs as u128) * (vt as u128) / ((vt - q) as u128) - vs as u128;
                let actual = doors_v1::math::reserve(vs, vt, q);
                if exact > u64::MAX as u128 {
                    assert!(actual.is_err());
                } else {
                    assert_eq!(actual.unwrap() as u128, exact);
                }
            }
        }
    }
}

#[test]
fn audit_external_authorities_cannot_transfer_vault_tokens() {
    let mut f = Fixture::new(1000);
    f.trade(Some(0), true, 1_010_000_000);
    f.trade(None, true, 1_010_000_000);
    f.retire();
    let r = f.r();
    let d = f.doors[0].clone();
    let user_room = ata(f.user.pubkey(), r.room_mint, spl_token_2022_interface::ID);
    for authority in [f.user.pubkey(), f.matcher.pubkey()] {
        for (source, mint, destination) in [
            (r.room_vault, r.room_mint, user_room),
            (r.retired_vault, r.room_mint, user_room),
            (d.vault, d.mint, d.user),
            (d.backing, r.room_mint, user_room),
        ] {
            assert!(f.balance(source) > 0);
            f.fail(
                spl_token_2022_interface::instruction::transfer_checked(
                    &spl_token_2022_interface::ID,
                    &source,
                    &mint,
                    &destination,
                    &authority,
                    &[],
                    1,
                    6,
                )
                .unwrap(),
                authority == f.matcher.pubkey(),
            );
            f.audit();
        }
    }
}

fn audit_send_as(f: &mut Fixture, signer: &Keypair, ix: Instruction) {
    let tx = Transaction::new(
        &[signer],
        Message::new(
            &[
                ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                ix,
            ],
            Some(&signer.pubkey()),
        ),
        f.svm.latest_blockhash(),
    );
    f.svm.send_transaction(tx).unwrap();
}

#[test]
fn fee_increases_reject_unchanged_signed_launches_and_conversions() {
    let mut evidence = Vec::new();
    for kind in 0..3 {
        let mut f = Fixture::empty(0);
        if kind != 0 {
            f.create(launch("Fee race room"), None);
        }
        if kind == 2 {
            f.open(launch("Fee race door"));
            f.trade(Some(0), true, 1_010_000_000);
        }
        let attacker = Keypair::new_from_array([33; 32]);
        f.svm.airdrop(&attacker.pubkey(), 100_000_000).unwrap();
        let mut s = defaults(f.matcher.pubkey(), attacker.pubkey());
        f.send(
            instr(
                a::UpdateConfig {
                    admin: f.user.pubkey(),
                    config: f.cfg,
                },
                ix::UpdateConfig {
                    settings: s.clone(),
                    new_admin: attacker.pubkey(),
                },
            ),
            false,
            "audit_config",
        );
        // These exact bytes are signed while the flat fee and maximum are zero.
        let operation = match kind {
            0 => f.create_ix(launch("Signed fee race room"), None),
            1 => f.open_ix(launch("Signed fee race door"), None),
            _ => f.convert_ix(0, 1, 1),
        };
        let signers = if kind == 2 {
            vec![&f.user]
        } else {
            vec![&f.user, &f.matcher]
        };
        let pending = Transaction::new(
            &signers,
            Message::new(
                &[
                    ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                    operation,
                ],
                Some(&f.user.pubkey()),
            ),
            f.svm.latest_blockhash(),
        );
        let signed_message = pending.message_data();
        let fee = 1_000_000_000;
        match kind {
            0 => {
                s.room_fee_lamports = fee - 1;
                s.door_fee_lamports = 1;
            }
            1 => s.door_fee_lamports = fee,
            _ => s.convert_fee_lamports = fee,
        }
        audit_send_as(
            &mut f,
            &attacker,
            instr(
                a::UpdateConfig {
                    admin: attacker.pubkey(),
                    config: p(&[b"config"]),
                },
                ix::UpdateConfig {
                    settings: s,
                    new_admin: attacker.pubkey(),
                },
            ),
        );
        pending.verify().unwrap();
        assert_eq!(pending.message_data(), signed_message);
        let before: BTreeMap<_, _> = pending
            .message
            .account_keys
            .iter()
            .map(|key| (*key, f.svm.get_account(key)))
            .collect();
        let victim_before = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
        let network_fee = 5000 * pending.signatures.len() as u64;
        let failure = f
            .svm
            .send_transaction(pending)
            .expect_err("fee increase must reject unchanged signed bytes");
        assert!(
            format!("{:?}", failure.err).contains("Custom("),
            "{failure:#?}"
        );
        assert!(
            failure
                .meta
                .logs
                .iter()
                .any(|line| line.contains("Error Code: FeeLimit.")),
            "{failure:#?}"
        );
        for (key, account) in before {
            if key != f.user.pubkey() {
                assert_eq!(
                    account,
                    f.svm.get_account(&key),
                    "fee rejection changed {key}"
                );
            }
        }
        let debit = victim_before - f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
        assert_eq!(debit, network_fee, "only network fees may be debited");
        if kind != 0 {
            f.audit();
        }
        evidence.push(
            json!({"operation": (["create_room", "open_door", "convert"][kind]),
            "signed_max_fee_lamports": 0, "execution_fee_lamports": fee,
            "signed_message_unchanged": true, "rejected_with": "FeeLimit",
            "victim_debit_lamports": debit, "network_fee_lamports": network_fee,
            "all_other_accounts_unchanged": true}),
        );
    }
    let out =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification/audit_fee_race.json");
    std::fs::write(out, serde_json::to_string_pretty(&evidence).unwrap() + "\n").unwrap();
}

#[test]
fn flat_fee_limits_include_combined_launch_fees_and_allow_equal_or_lower_fees() {
    let mut f = Fixture::empty(0);
    let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
    s.room_fee_lamports = 7;
    s.door_fee_lamports = 11;
    s.convert_fee_lamports = 13;
    audit_settings(&mut f, s.clone());
    let mut l = launch("Flat fee room");
    l.max_fee_lamports = 17;
    f.fail_error(f.create_ix(l.clone(), None), true, Some("FeeLimit"));
    // Legacy instruction data has no cap and must fail deserialization.
    let mut legacy = f.create_ix(l.clone(), None);
    legacy.data.truncate(legacy.data.len() - 8);
    f.fail_error(legacy, true, Some("InstructionDidNotDeserialize"));
    l.max_fee_lamports = 18;
    f.create(l, None);
    assert_eq!(f.r().protocol_accrued_sol, 18);
    let mut l = launch("Flat fee door");
    l.max_fee_lamports = 10;
    f.fail_error(f.open_ix(l.clone(), None), true, Some("FeeLimit"));
    let mut legacy = f.open_ix(l.clone(), None);
    legacy.data.truncate(legacy.data.len() - 8);
    f.fail_error(legacy, true, Some("InstructionDidNotDeserialize"));
    l.max_fee_lamports = 11;
    f.open(l);
    assert_eq!(f.r().protocol_accrued_sol, 29);
    f.trade(Some(0), true, 1_010_000_000);
    let with_cap = |f: &Fixture, cap| {
        let mut ix = f.convert_ix(0, 1, 1);
        ix.data = ix::Convert {
            amount: 1,
            max_fee_lamports: cap,
        }
        .data();
        ix
    };
    f.fail_error(with_cap(&f, 12), false, Some("FeeLimit"));
    let mut legacy = with_cap(&f, 13);
    legacy.data.truncate(legacy.data.len() - 8);
    f.fail_error(legacy, false, Some("InstructionDidNotDeserialize"));
    let before = f.r().protocol_accrued_sol;
    f.checked(with_cap(&f, 13), false, "convert");
    assert_eq!(f.r().protocol_accrued_sol, before + 13);
    // A signed ceiling is not an exact-fee requirement: lower fees are safe.
    let pending_ix = with_cap(&f, 13);
    let pending = Transaction::new(
        &[&f.user],
        Message::new(
            &[
                ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                pending_ix,
            ],
            Some(&f.user.pubkey()),
        ),
        f.svm.latest_blockhash(),
    );
    s.convert_fee_lamports = 3;
    audit_settings(&mut f, s);
    let before = f.r().protocol_accrued_sol;
    f.svm.send_transaction(pending).unwrap();
    assert_eq!(f.r().protocol_accrued_sol, before + 3);
    f.audit();
}

#[test]
fn config_rejects_total_launch_fee_overflow_and_confiscatory_trade_fees() {
    let mut f = Fixture::new(0);
    for kind in 0..2 {
        let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
        if kind == 0 {
            s.room_fee_lamports = u64::MAX;
            s.door_fee_lamports = 1;
        } else {
            s.fee_bps = 10_000;
        }
        f.fail_error(
            instr(
                a::UpdateConfig {
                    admin: f.user.pubkey(),
                    config: f.cfg,
                },
                ix::UpdateConfig {
                    settings: s,
                    new_admin: f.user.pubkey(),
                },
            ),
            false,
            Some("BadConfig"),
        );
    }
    f.trade(Some(0), true, 1_010_000);
    f.trade(Some(0), false, f.balance(f.doors[0].user));
    f.audit();
}

#[test]
fn door_nonces_do_not_contend_and_a_dropped_open_blocks_nothing() {
    let mut f = Fixture::new(0);
    let mut a = launch("Concurrent A");
    a.door_nonce = 0x1111_1111_1111_1111;
    let mut b = launch("Concurrent B");
    b.door_nonce = 0x2222_2222_2222_2222;
    // Both are built (and co-signed) against the same room state.
    let ia = f.open_ix(a.clone(), None);
    let ib = f.open_ix(b.clone(), None);
    assert_ne!(ia.accounts, ib.accounts);
    // A is "dropped": B lands first, and nothing about A's reservation blocks it.
    f.checked(ib, true, "open_door");
    let kb = DoorKeys::new(f.room, b.door_nonce, f.user.pubkey());
    assert_eq!(f.r().door_count, 2);
    let db = Door::try_deserialize(&mut &f.svm.get_account(&kb.door).unwrap().data[..]).unwrap();
    assert_eq!((db.index, db.nonce), (1, b.door_nonce));
    // A built earlier still lands afterwards: its address never depended on door_count.
    f.checked(ia, true, "open_door");
    let ka = DoorKeys::new(f.room, a.door_nonce, f.user.pubkey());
    let da = Door::try_deserialize(&mut &f.svm.get_account(&ka.door).unwrap().data[..]).unwrap();
    assert_eq!((da.index, da.nonce, f.r().door_count), (2, a.door_nonce, 3));
    f.doors.push(kb);
    f.doors.push(ka);
    f.audit();
}

#[test]
fn door_nonce_collisions_fail_cleanly_and_door_zero_is_nonce_zero() {
    let mut f = Fixture::new(0);
    let mut l = launch("First nonce");
    l.door_nonce = 0x3333;
    f.open(l.clone());
    // Re-using an existing door's nonce cannot overwrite it: the PDA exists.
    let mut again = launch("Same nonce, other face");
    again.door_nonce = 0x3333;
    f.fail(f.open_ix(again, None), true);
    // Nonce 0 is door 0's address in every room, so open_door with it cannot create a door.
    let mut zero = launch("Zero nonce");
    zero.door_nonce = 0x4444; // build with a real nonce, then point it at door 0 with nonce 0
    let mut ix = f.open_ix(zero.clone(), None);
    let fresh = DoorKeys::new(f.room, 0x4444, f.user.pubkey());
    let d0 = DoorKeys::new(f.room, 0, f.user.pubkey());
    for m in ix.accounts.iter_mut() {
        for (from, to) in [
            (fresh.door, d0.door),
            (fresh.mint, d0.mint),
            (fresh.vault, d0.vault),
            (fresh.backing, d0.backing),
            (fresh.user, d0.user),
        ] {
            if m.pubkey == from {
                m.pubkey = to;
            }
        }
    }
    let mut z = f.fill(zero, false);
    z.door_nonce = 0;
    ix.data = ix::OpenDoor { launch: z }.data();
    f.fail(ix, true);
    assert_eq!(f.r().door_count, 2);
    // create_room must use nonce 0 for door 0.
    let mut g = Fixture::empty(0);
    let mut bad = launch("Non-zero door 0 nonce");
    bad.door_nonce = 9;
    g.fail_error(g.create_ix(bad, None), true, Some("DoorNonce"));
}

#[test]
fn launch_expiry_window_is_enforced_on_both_launch_paths() {
    let mut f = Fixture::empty(0);
    let slot = 50_000;
    f.svm.warp_to_slot(slot);
    let with = |name: &str, expires: u64| {
        let mut l = launch(name);
        l.expires_at_slot = expires;
        l
    };
    // create_room: one slot late, and one slot too far ahead, both fail.
    f.fail_error(
        f.create_ix(with("Expiry room", slot - 1), None),
        true,
        Some("Expired"),
    );
    f.fail_error(
        f.create_ix(
            with("Expiry room", slot + MAX_LAUNCH_WINDOW_SLOTS + 1),
            None,
        ),
        true,
        Some("Expired"),
    );
    // Inclusive at the current slot.
    f.create(with("Expiry room", slot), None);
    // open_door: the same three boundaries.
    f.fail_error(
        f.open_ix(with("Expiry door", slot - 1), None),
        true,
        Some("Expired"),
    );
    f.fail_error(
        f.open_ix(
            with("Expiry door", slot + MAX_LAUNCH_WINDOW_SLOTS + 1),
            None,
        ),
        true,
        Some("Expired"),
    );
    f.open(with("Expiry door", slot + MAX_LAUNCH_WINDOW_SLOTS));
    // A launch signed for this window is dead once the chain moves past it.
    let late = f.open_ix(with("Held decision", slot + 10), None);
    f.svm.warp_to_slot(slot + 11);
    f.fail_error(late, true, Some("Expired"));
}

// Attribution of buy CU to the settle-before-buy retirement (8ce373f). Same room, same
// route, same input; the only difference between paired samples is whether
// `pending_reserve_sol` is non-zero when the buy executes.
#[test]
fn buy_cu_attribution_with_and_without_pending_settlement() {
    let token_prefix = format!("Program {} consumed ", spl_token_2022_interface::ID);
    let root_prefix = format!("Program {ID} consumed ");
    let mut rows = Vec::new();
    let mut f = Fixture::new(0);
    // (step, route, retire first). Room buys put the door share into pending, door buys do not.
    for (step, route, clear) in [
        (0, None, false),
        (1, None, false),
        (2, None, true),
        (3, None, false),
        (4, Some(0), false),
        (5, Some(0), true),
    ] {
        if clear {
            // Clear the backlog so this buy settles nothing.
            f.retire();
        }
        let pending = f.r().pending_reserve_sol;
        let name = if route.is_some() {
            "attr_buy_door"
        } else {
            "attr_buy_room"
        };
        let meta = f.checked(f.trade_ix(route, true, 1_010_000, 0), false, name);
        f.audit();
        let root = meta.logs.iter().find_map(|l| {
            l.strip_prefix(&root_prefix)
                .and_then(|s| s.split_whitespace().next())
                .and_then(|n| n.parse::<u64>().ok())
        });
        let token_cpis: Vec<u64> = meta
            .logs
            .iter()
            .filter_map(|l| {
                l.strip_prefix(&token_prefix)
                    .and_then(|s| s.split_whitespace().next())
                    .and_then(|n| n.parse::<u64>().ok())
            })
            .collect();
        rows.push(
            json!({"step":step,"route":if route.is_some(){"door"}else{"room"},
            "pending_before":pending,"settled":pending>0,"program_cu":root,
            "token_cpis":token_cpis.len(),"token_cpi_cu":token_cpis}),
        );
    }
    let get = |i: usize| rows[i]["program_cu"].as_u64().unwrap();
    let settled = |i: usize| rows[i]["settled"].as_bool().unwrap();
    let cpis = |i: usize| rows[i]["token_cpis"].as_u64().unwrap();
    // Steps 0, 2 and 5 settle nothing; 1, 3 and 4 settle a non-zero backlog.
    assert!(!settled(0) && settled(1) && !settled(2) && settled(3) && settled(4) && !settled(5));
    assert!(cpis(1) == cpis(0) + 1 && cpis(3) == cpis(2) + 1 && cpis(4) == cpis(5) + 1);
    let out = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification");
    std::fs::write(
        out.join("cu_buy_attribution.json"),
        serde_json::to_string_pretty(&json!({
            "kind":"executed compiled Anchor SBF in LiteSVM; same fixture, same input (1,010,000 lamports)",
            "rows":rows,
            "room_buy_delta_cu":[get(1) as i64 - get(0) as i64, get(3) as i64 - get(2) as i64],
            "door_buy_delta_cu":get(4) as i64 - get(5) as i64
        }))
        .unwrap()
            + "\n",
    )
    .unwrap();
}

// Worst case for the never-freed 32 KiB SBF heap: maximum metadata on both mints,
// every writable launch account prefunded by a third party (so creation takes the
// transfer + allocate + assign path), non-zero flat fees and an atomic first buy
// that also settles a pending backlog. Anyone can prefund a PDA, so a launch that
// only fits the heap when unfunded can be griefed.
#[test]
fn prefunded_maximum_metadata_launches_fit_the_heap() {
    let mut f = Fixture::empty(0);
    let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
    settings.room_fee_lamports = 7;
    settings.door_fee_lamports = 11;
    f.send(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        "update_config",
    );
    let max = |name: &str, fee: u64, buy: u64| {
        let mut l = launch(&format!("{name}{}", "x".repeat(32 - name.len())));
        l.symbol = "Y".repeat(10);
        l.uri = "u".repeat(200);
        l.max_fee_lamports = fee;
        l.first_buy_lamports = buy;
        l
    };
    let rent = f.svm.minimum_balance_for_rent_exemption(0);
    let l = max("Prefunded max room", 18, 1_010_000_000);
    let ix = f.create_ix(l.clone(), None);
    for account in &ix.accounts {
        if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
            f.svm.airdrop(&account.pubkey, rent).unwrap();
        }
    }
    f.create(l, None);
    // A room-route buy leaves a pending backlog, so the next first buy settles it.
    f.trade(None, true, 1_010_000);
    assert!(f.r().pending_reserve_sol > 0);
    let l = max("Prefunded max door", 11, 101_000_000);
    let ix = f.open_ix(l.clone(), None);
    for account in &ix.accounts {
        if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
            f.svm.airdrop(&account.pubkey, rent).unwrap();
        }
    }
    f.open(l);
    assert_eq!(f.r().pending_reserve_sol, 0);
    assert!(f.d(1).backing > 0);
    // The matcher service signs launches with a 400,000 CU limit (MATCHER_CU_LIMIT default);
    // a third party's prefunding must not push a co-signed launch past it.
    let create_cu = *f.cus["create_room"].last().unwrap();
    let open_cu = *f.cus["open_door"].last().unwrap();
    println!("PREFUNDED_MAX_CU create_room={create_cu} open_door={open_cu}");
    assert!(create_cu < 400_000 && open_cu < 400_000);
}

// The takeover paths deserialise a second Room (`old_holder`) on top of the worst case
// above: every new account prefunded, non-zero fees, first buy. The create_room takeover
// uses the largest metadata the matcher service can sign in a legacy transaction
// (name 32, symbol 10, URI 70: services/matcher txbuild size check); open_door uses the
// program maximum (URI 200), which fits a legacy transaction. The program maximum for a
// create_room takeover needs a v0 transaction. The former M-7 reproduction below
// is now required to pass as well, using the same stock heap.
#[test]
fn prefunded_maximum_metadata_takeovers_fit_the_heap() {
    takeover_heap_case(70);
}

/// M-7 regression: maximum-size takeover with every new account prefunded.
/// Runs with the stock 32 KiB heap, without a larger frame or custom allocator.
#[test]
fn prefunded_v0_maximum_takeover_fits_the_heap() {
    takeover_heap_case(200);
}

fn takeover_heap_case(create_uri: usize) {
    let mut f = Fixture::empty(0);
    let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
    settings.room_fee_lamports = 7;
    settings.door_fee_lamports = 11;
    f.send(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings,
                new_admin: f.user.pubkey(),
            },
        ),
        false,
        "update_config",
    );
    let max = |name: &str, fee: u64, buy: u64| {
        let mut l = launch(&format!("{name}{}", "x".repeat(32 - name.len())));
        l.symbol = "Y".repeat(10);
        l.uri = "u".repeat(200);
        l.max_fee_lamports = fee;
        l.first_buy_lamports = buy;
        l
    };
    let prefund = |f: &mut Fixture, ix: &Instruction| {
        let rent = f.svm.minimum_balance_for_rent_exemption(0);
        for account in &ix.accounts {
            if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
                f.svm.airdrop(&account.pubkey, rent).unwrap();
            }
        }
    };
    let mut next_room = |f: &mut Fixture, rid: u64| {
        f.rid = rid;
        f.room = p(&[b"room", &rid.to_le_bytes()]);
        f.doors.clear();
    };
    // Room A holds identity "Taken"; B holds "Door identity". Both go dead.
    f.create(max("Taken", 18, 0), None);
    let a_room = f.room;
    next_room(&mut f, 0x51c3_0aa7_9e44_1d02);
    f.create(max("Door identity", 18, 0), None);
    let b_room = f.room;
    f.time(3600);
    // create_room takeover of A's exact identity, prefunded, with a first buy.
    next_room(&mut f, 0x7d21_93be_04f5_c6a8);
    let mut l = max("Taken", 18, 1_010_000_000);
    l.uri = "u".repeat(create_uri);
    let ix = f.create_ix(l.clone(), Some(a_room));
    prefund(&mut f, &ix);
    f.create(l, Some(a_room));
    let create_cu = *f.cus["create_room"].last().unwrap();
    // A room-route buy leaves a backlog for the next first buy to settle.
    f.trade(None, true, 1_010_000);
    assert!(f.r().pending_reserve_sol > 0);
    // open_door into this (young, live) room with B's identity: B is the dead old holder.
    let l = max("Door identity", 11, 101_000_000);
    let ix = f.open_ix(l, Some(b_room));
    prefund(&mut f, &ix);
    f.checked(ix, true, "open_door");
    f.audit();
    let open_cu = *f.cus["open_door"].last().unwrap();
    println!("PREFUNDED_TAKEOVER_CU create_room={create_cu} open_door={open_cu}");
    assert!(create_cu < 400_000 && open_cu < 400_000);
}

// Instruction-trace budget of launches. A transaction may hold at most 64 instruction entries
// (top-level instructions plus every CPI, Agave MAX_INSTRUCTION_TRACE_LENGTH). Prefunding a PDA turns
// its one create_account CPI into transfer + allocate + assign, so a third party can raise a launch's
// trace use. Shapes are the matcher service's: [cu_limit, launch] and, with a priority fee,
// [cu_limit, cu_price, launch]. Ordinary metadata; the trace does not depend on metadata length.
#[test]
fn launch_instruction_trace_budget() {
    fn shaped(f: &mut Fixture, ix: Instruction, price: bool, extra: bool) -> (bool, usize, String) {
        f.svm.expire_blockhash();
        let mut ixs = vec![ComputeBudgetInstruction::set_compute_unit_limit(400_000)];
        if price {
            ixs.push(ComputeBudgetInstruction::set_compute_unit_price(1));
        }
        if extra {
            // Real composition margin: two additional valid instructions. The
            // stock heap size is intentional; M-7 must fit without enlarging it.
            ixs.push(ComputeBudgetInstruction::request_heap_frame(32 * 1024));
            ixs.push(
                ComputeBudgetInstruction::set_loaded_accounts_data_size_limit(64 * 1024 * 1024),
            );
        }
        ixs.push(ix);
        let tx = Transaction::new(
            &vec![&f.user, &f.matcher],
            Message::new(&ixs, Some(&f.user.pubkey())),
            f.svm.latest_blockhash(),
        );
        let count = |logs: &[String]| logs.iter().filter(|l| l.contains(" invoke [")).count();
        match f.svm.send_transaction(tx) {
            Ok(m) => (true, count(&m.logs), String::new()),
            Err(e) => (false, count(&e.meta.logs), format!("{:?}", e.err)),
        }
    }
    let prefund = |f: &mut Fixture, ix: &Instruction| {
        let rent = f.svm.minimum_balance_for_rent_exemption(0);
        for account in &ix.accounts {
            if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
                f.svm.airdrop(&account.pubkey, rent).unwrap();
            }
        }
    };
    let mut rows = Vec::new();
    for (prefunded, price, extra) in [
        (false, false, false),
        (false, true, false),
        (true, false, false),
        (true, true, false),
        (true, true, true),
    ] {
        let mut f = Fixture::empty(0);
        let mut l = launch("Trace room");
        l.first_buy_lamports = 1_010_000_000;
        let ix = f.create_ix(l, None);
        if prefunded {
            prefund(&mut f, &ix);
        }
        let (ok, invokes, err) = shaped(&mut f, ix, price, extra);
        rows.push(
            json!({"instruction":"create_room","first_buy":true,"prefunded":prefunded,
            "priority_fee_instruction":price,"extra_budget_instructions":if extra {2} else {0},
            "succeeded":ok,"logged_invocations":invokes,"error":err}),
        );
        let mut g = Fixture::new(0);
        let mut l = launch("Trace door");
        l.first_buy_lamports = 101_000_000;
        let ix = g.open_ix(l, None);
        if prefunded {
            prefund(&mut g, &ix);
        }
        let (ok, invokes, err) = shaped(&mut g, ix, price, extra);
        rows.push(
            json!({"instruction":"open_door","first_buy":true,"prefunded":prefunded,
            "priority_fee_instruction":price,"extra_budget_instructions":if extra {2} else {0},
            "succeeded":ok,"logged_invocations":invokes,"error":err}),
        );
    }
    for r in &rows {
        println!("TRACE {r}");
        assert!(r["succeeded"].as_bool().unwrap(), "launch failed: {r}");
        assert!(r["logged_invocations"].as_u64().unwrap() <= 54,
            "keep at least ten trace entries free, including a priority fee and extra instructions: {r}");
    }
    let out = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification");
    std::fs::write(
        out.join("trace_budget.json"),
        serde_json::to_string_pretty(&json!({"max_instruction_trace_length":64,
            "note":"logged_invocations counts runtime 'invoke [n]' log lines (programs invoked, top level and CPI)",
            "rows":rows}))
        .unwrap()
            + "\n",
    )
    .unwrap();
}
