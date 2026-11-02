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
    fn new(room: Pubkey, i: u32, user: Pubkey) -> Self {
        let door = p(&[b"door", room.as_ref(), &i.to_le_bytes()]);
        let mint = p(&[b"door_mint", room.as_ref(), &i.to_le_bytes()]);
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
        let before = self.svm.get_account(&self.room);
        let reserve = self.svm.get_account(&p(&[b"reserve", self.room.as_ref()]));
        let tx = Transaction::new(
            &if matcher {
                vec![&self.user, &self.matcher]
            } else {
                vec![&self.user]
            },
            Message::new(&[ix], Some(&self.user.pubkey())),
            self.svm.latest_blockhash(),
        );
        assert!(self.svm.send_transaction(tx).is_err());
        assert_eq!(before, self.svm.get_account(&self.room));
        assert_eq!(
            reserve,
            self.svm.get_account(&p(&[b"reserve", self.room.as_ref()]))
        );
    }
    fn create_ix(&self, l: Launch, holder: Option<Pubkey>) -> Instruction {
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
        let d = DoorKeys::new(self.room, self.r().door_count, self.user.pubkey());
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
        let d = DoorKeys::new(self.room, self.r().door_count, self.user.pubkey());
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
            ix::Convert { amount: n },
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
                    p(&[b"door", self.room.as_ref(), &d.index.to_le_bytes()])
                );
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
fn crossing_buy_caps_on_accounted_reserve_and_stops_at_complete() {
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
    f.fail(f.trade_ix(Some(0), false, 1, 0), false);
    f.open(launch("Complete door"));
    f.convert(0, 1, 1);
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
    let before = f.r();
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
    f.fail(f.trade_ix(Some(0), true, 101, 0), false);
    f.fail(f.open_ix(launch("Paused"), None), true);
    f.claim(1, 0);
    f.claim(2, 0);
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
    assert_eq!(fold("érn-vv 0".as_bytes()), "éRNVVO".as_bytes());
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
