//! Devnet runner for doors_v1: initialise Config, read it back, run the live
//! smoke sequence and the expected-failure cases. Every transaction it sends is
//! recorded with signature, slot and compute units in a JSON report.
//!
//! Keypairs are read from files in a directory given on the command line.
//! Nothing secret is printed or written to a report. Usage:
//!   doors-devnet init   <keys_dir> <settings.json> <report.json>
//!   doors-devnet config <settings.json> <report.json>
//!   doors-devnet smoke  <keys_dir> <report.json>
//!   doors-devnet fail   <keys_dir> <smoke_report.json> <report.json>
//! RPC endpoint: $DOORS_RPC, default https://api.devnet.solana.com.
use anchor_lang::{
    prelude::Pubkey, AccountDeserialize, AnchorDeserialize, Discriminator, InstructionData,
    ToAccountMetas,
};
use anyhow::{anyhow, bail, Context, Result};
use doors_v1::{accounts as a, instruction as ix, math::U, state::*, vaults::ATA, Trade, ID};
use serde_json::{json, Value};
use solana_compute_budget_interface::ComputeBudgetInstruction;
use solana_hash::Hash;
use solana_instruction::{AccountMeta, Instruction};
use solana_keypair::{read_keypair_file, Keypair};
use solana_message::Message;
use solana_signature::Signature;
use solana_signer::Signer;
use solana_transaction::Transaction;
use spl_token_2022_interface::{
    extension::{BaseStateWithExtensions, StateWithExtensions},
    state::{Account as TokenAccount, Mint},
};
use std::{fs, io::Read, process::Command, str::FromStr, thread::sleep, time::Duration};

const DEFAULT_RPC: &str = "https://api.devnet.solana.com";
fn rpc_url() -> String {
    std::env::var("DOORS_RPC").unwrap_or_else(|_| DEFAULT_RPC.to_string())
}
const CU_LIMIT: u32 = 1_400_000; // the same limit the SVM tests request
const T22: Pubkey = spl_token_2022_interface::ID;
const CLASSIC: Pubkey = spl_token_interface::ID;
const WSOL: Pubkey = spl_token_interface::native_mint::ID;
const SYS: Pubkey = anchor_lang::system_program::ID;

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
fn key(dir: &str, name: &str) -> Result<Keypair> {
    read_keypair_file(format!("{dir}/{name}.json")).map_err(|e| anyhow!("read {name}: {e}"))
}
fn program_data() -> Pubkey {
    Pubkey::find_program_address(
        &[ID.as_ref()],
        &anchor_lang::solana_program::bpf_loader_upgradeable::ID,
    )
    .0
}

/// Account as returned by getAccountInfo (base64 data decoded).
struct Account {
    lamports: u64,
    data: Vec<u8>,
    owner: Pubkey,
}

/// Minimal JSON-RPC client. HTTP goes through `curl`, which uses this
/// environment's proxy and CA bundle; the 4.x RPC client crates do not compile
/// against the pinned transaction crates (two incompatible wincode versions).
struct Chain {
    log: Vec<Value>,
}
impl Chain {
    fn new() -> Self {
        Self { log: vec![] }
    }
    fn rpc(&self, method: &str, params: Value) -> Result<Value> {
        let body =
            json!({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).to_string();
        for attempt in 0..6 {
            let out = Command::new("curl")
                .args([
                    "-sS",
                    "--fail-with-body",
                    "-m",
                    "60",
                    "-H",
                    "content-type: application/json",
                    "-d",
                    &body,
                    &rpc_url(),
                ])
                .output()
                .context("run curl")?;
            let text = String::from_utf8_lossy(&out.stdout).to_string();
            let v: Value = match serde_json::from_str(&text) {
                Ok(v) => v,
                Err(_) => {
                    // Transient HTTP failure (e.g. 429): back off and retry.
                    sleep(Duration::from_millis(1500 << attempt));
                    continue;
                }
            };
            if let Some(e) = v.get("error") {
                if e["code"] == json!(429) {
                    sleep(Duration::from_millis(1500 << attempt));
                    continue;
                }
                bail!("{method}: {e}");
            }
            return Ok(v["result"].clone());
        }
        bail!("{method}: no response after retries")
    }
    fn blockhash(&self) -> Result<Hash> {
        let r = self.rpc("getLatestBlockhash", json!([{"commitment": "confirmed"}]))?;
        Hash::from_str(
            r["value"]["blockhash"]
                .as_str()
                .ok_or_else(|| anyhow!("blockhash"))?,
        )
        .map_err(|e| anyhow!("{e:?}"))
    }
    fn tx(
        &self,
        ixs: &[Instruction],
        payer: &Keypair,
        signers: &[&Keypair],
    ) -> Result<Transaction> {
        let mut all = vec![ComputeBudgetInstruction::set_compute_unit_limit(CU_LIMIT)];
        all.extend_from_slice(ixs);
        let bh = self.blockhash()?;
        let mut v: Vec<&Keypair> = vec![payer];
        v.extend(
            signers
                .iter()
                .copied()
                .filter(|k| k.pubkey() != payer.pubkey()),
        );
        Ok(Transaction::new(
            &v,
            Message::new(&all, Some(&payer.pubkey())),
            bh,
        ))
    }
    fn submit(
        &self,
        t: &Transaction,
        skip_preflight: bool,
    ) -> Result<std::result::Result<Signature, String>> {
        let wire = bincode::serialize(t)?;
        let b64 = b64_encode(&wire);
        let params = json!([b64, {"encoding": "base64", "skipPreflight": skip_preflight, "preflightCommitment": "confirmed", "maxRetries": 5}]);
        match self.rpc("sendTransaction", params) {
            Ok(r) => Ok(Ok(Signature::from_str(
                r.as_str().ok_or_else(|| anyhow!("signature"))?,
            )
            .map_err(|e| anyhow!("{e}"))?)),
            Err(e) => Ok(Err(e.to_string())),
        }
    }
    fn wait(&self, sig: &Signature) -> Result<Value> {
        for _ in 0..90 {
            sleep(Duration::from_millis(1000));
            let r = self.rpc(
                "getSignatureStatuses",
                json!([[sig.to_string()], {"searchTransactionHistory": true}]),
            )?;
            let st = &r["value"][0];
            if !st.is_null()
                && (st["confirmationStatus"] == json!("confirmed")
                    || st["confirmationStatus"] == json!("finalized"))
            {
                return Ok(st.clone());
            }
        }
        bail!("no confirmation for {sig}")
    }
    /// Send, confirm, then read back slot, CU and logs. Records the result.
    fn send(
        &mut self,
        name: &str,
        ixs: &[Instruction],
        payer: &Keypair,
        signers: &[&Keypair],
    ) -> Result<Value> {
        let t = self.tx(ixs, payer, signers)?;
        let sig = self
            .submit(&t, false)?
            .map_err(|e| anyhow!("{name}: {e}"))?;
        self.wait(&sig)?;
        self.record(name, &sig, true)
    }
    /// Send with preflight skipped so a program failure lands on-chain, and record it.
    /// A transaction the cluster rejects before execution (bad signature) never lands;
    /// that is recorded with the RPC's error instead.
    fn send_fail(&mut self, name: &str, t: Transaction) -> Result<Value> {
        self.send_fail_with(name, t, true)
    }
    /// `skip_preflight = false` makes the RPC verify signatures and report the reason;
    /// a forged signature is otherwise dropped silently by the leader and never lands.
    fn send_fail_with(
        &mut self,
        name: &str,
        t: Transaction,
        skip_preflight: bool,
    ) -> Result<Value> {
        match self.submit(&t, skip_preflight)? {
            Err(e) => {
                println!("{name}: rejected before execution: {e}");
                let rec = json!({"name": name, "landed": false, "rpc_error": e});
                self.log.push(rec.clone());
                Ok(rec)
            }
            Ok(sig) => {
                let st = self.wait(&sig)?;
                if st["err"].is_null() {
                    bail!("{name}: expected failure but transaction succeeded: {sig}");
                }
                self.record(name, &sig, false)
            }
        }
    }
    fn record(&mut self, name: &str, sig: &Signature, expect_ok: bool) -> Result<Value> {
        let mut found = Value::Null;
        for _ in 0..30 {
            let r = self.rpc("getTransaction", json!([sig.to_string(), {"encoding": "json", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}]))?;
            if !r.is_null() {
                found = r;
                break;
            }
            sleep(Duration::from_millis(1000));
        }
        if found.is_null() {
            bail!("{name}: transaction {sig} not found");
        }
        let meta = &found["meta"];
        let logs: Vec<String> = meta["logMessages"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|l| l.as_str().map(String::from))
            .collect();
        // Program-inclusive CU (its CPIs included, compute-budget instruction excluded):
        // the same quantity the SVM report measures.
        let prefix = format!("Program {ID} consumed ");
        let program_cu = logs.iter().find_map(|l| {
            l.strip_prefix(&prefix)
                .and_then(|r| r.split_whitespace().next())
                .and_then(|n| n.parse::<u64>().ok())
        });
        let err = if meta["err"].is_null() {
            None
        } else {
            Some(meta["err"].to_string())
        };
        let error_log = logs
            .iter()
            .find(|l| l.contains("Error Code:") || l.contains("failed:"))
            .cloned();
        if expect_ok && err.is_some() {
            bail!("{name} failed: {err:?} {error_log:?}");
        }
        let events: Vec<String> = logs
            .iter()
            .filter_map(|l| l.strip_prefix("Program data: ").map(String::from))
            .collect();
        let rec = json!({
            "name": name, "signature": sig.to_string(), "slot": found["slot"], "block_time": found["blockTime"],
            "landed": true, "ok": err.is_none(), "program_cu": program_cu, "transaction_cu": meta["computeUnitsConsumed"],
            "fee_lamports": meta["fee"], "error": err, "error_log": error_log, "events": events,
        });
        println!(
            "{name}: slot {} sig {} program_cu {:?} ok {}",
            found["slot"],
            sig,
            program_cu,
            err.is_none()
        );
        self.log.push(rec.clone());
        Ok(rec)
    }
    fn account_at(&self, k: &Pubkey) -> Result<(u64, Option<Account>)> {
        let r = self.rpc(
            "getAccountInfo",
            json!([k.to_string(), {"encoding": "base64", "commitment": "confirmed"}]),
        )?;
        let slot = r["context"]["slot"].as_u64().unwrap_or(0);
        let v = &r["value"];
        if v.is_null() {
            return Ok((slot, None));
        }
        let data = b64(v["data"][0].as_str().ok_or_else(|| anyhow!("data"))?)
            .ok_or_else(|| anyhow!("base64"))?;
        Ok((
            slot,
            Some(Account {
                lamports: v["lamports"].as_u64().ok_or_else(|| anyhow!("lamports"))?,
                data,
                owner: Pubkey::from_str(v["owner"].as_str().ok_or_else(|| anyhow!("owner"))?)
                    .map_err(|e| anyhow!("{e}"))?,
            }),
        ))
    }
    fn account(&self, k: &Pubkey) -> Result<Account> {
        self.account_at(k)?
            .1
            .ok_or_else(|| anyhow!("account {k} not found"))
    }
    fn slot(&self) -> Result<u64> {
        self.rpc("getSlot", json!([{"commitment": "confirmed"}]))?
            .as_u64()
            .ok_or_else(|| anyhow!("slot"))
    }
    fn rent(&self, len: usize) -> Result<u64> {
        self.rpc("getMinimumBalanceForRentExemption", json!([len]))?
            .as_u64()
            .ok_or_else(|| anyhow!("rent"))
    }
    fn room(&self, k: &Pubkey) -> Result<Room> {
        Ok(Room::try_deserialize(&mut &self.account(k)?.data[..])?)
    }
    fn door(&self, k: &Pubkey) -> Result<Door> {
        Ok(Door::try_deserialize(&mut &self.account(k)?.data[..])?)
    }
    fn balance(&self, k: &Pubkey) -> Result<u64> {
        Ok(
            StateWithExtensions::<TokenAccount>::unpack(&self.account(k)?.data)?
                .base
                .amount,
        )
    }
}

fn b64_encode(d: &[u8]) -> String {
    const A: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut s = String::new();
    for c in d.chunks(3) {
        let n = (c[0] as u32) << 16
            | (*c.get(1).unwrap_or(&0) as u32) << 8
            | *c.get(2).unwrap_or(&0) as u32;
        for i in 0..4 {
            if i <= c.len() {
                s.push(A[(n >> (18 - 6 * i) & 63) as usize] as char);
            } else {
                s.push('=');
            }
        }
    }
    s
}

fn settings_from(path: &str) -> Result<Settings> {
    let v: Value = serde_json::from_str(&fs::read_to_string(path)?)?;
    let u = |k: &str| -> Result<u64> {
        match &v[k] {
            Value::String(s) => s.parse::<u64>().map_err(|e| anyhow!("{k}: {e}")),
            Value::Number(n) => n.as_u64().ok_or_else(|| anyhow!("{k}: not u64")),
            _ => bail!("{k}: missing"),
        }
    };
    let pk = |k: &str| -> Result<Pubkey> {
        Pubkey::from_str(v[k].as_str().ok_or_else(|| anyhow!("{k}: missing"))?)
            .map_err(|e| anyhow!("{k}: {e}"))
    };
    let small = |k: &str| -> Result<u16> { Ok(u16::try_from(u(k)?)?) };
    Ok(Settings {
        protocol_fee_recipient: pk("protocol_fee_recipient")?,
        fee_bps: small("fee_bps")?,
        door_share_bps: small("door_share_bps")?,
        door_fee_lamports: u("door_fee_lamports")?,
        room_fee_lamports: u("room_fee_lamports")?,
        convert_fee_lamports: u("convert_fee_lamports")?,
        v_sol_lamports: u("v_sol_lamports")?,
        v_tok: u("v_tok")?,
        supply: u("supply")?,
        r_star_lamports: u("r_star_lamports")?,
        meteora_dynamic_config: pk("meteora_dynamic_config")?,
        graduation_trigger_lamports: u("graduation_trigger_lamports")?,
        paused: v["paused"]
            .as_bool()
            .ok_or_else(|| anyhow!("paused: missing"))?,
        matcher_authority: pk("matcher_authority")?,
        live_min_reserve_lamports: u("live_min_reserve_lamports")?,
        live_max_idle_seconds: u("live_max_idle_seconds")?,
        live_new_seconds: u("live_new_seconds")?,
        live_min_volume_lamports: u("live_min_volume_lamports")?,
        pool_min_window_lp_fee: u("pool_min_window_lp_fee")?,
        founder_share_bps: small("founder_share_bps")?,
    })
}

fn init(dir: &str, settings: &str, out: &str) -> Result<()> {
    let mut c = Chain::new();
    // initialize_config's signer must be the program's current upgrade authority.
    let admin = key(dir, "upgrade-authority")?;
    let s = settings_from(settings)?;
    let ixn = instr(
        a::InitializeConfig {
            admin: admin.pubkey(),
            config: p(&[b"config"]),
            program: ID,
            program_data: program_data(),
            system_program: SYS,
        },
        ix::InitializeConfig { settings: s },
    );
    c.send("initialize_config", &[ixn], &admin, &[])?;
    fs::write(
        out,
        serde_json::to_string_pretty(&json!({"program": ID.to_string(), "transactions": c.log}))?,
    )?;
    Ok(())
}

fn config(settings: &str, out: &str) -> Result<()> {
    let c = Chain::new();
    let s = settings_from(settings)?;
    let cfg_key = p(&[b"config"]);
    let (slot, acc) = c.account_at(&cfg_key)?;
    let acc = acc.ok_or_else(|| anyhow!("no Config account"))?;
    let k = Config::try_deserialize(&mut &acc.data[..])?;
    let pdata = c.account(&program_data())?;
    let ua = if pdata.data[12] == 1 {
        Pubkey::try_from(&pdata.data[13..45]).unwrap().to_string()
    } else {
        "None".into()
    };
    let rows: Vec<(&str, String, String)> = vec![
        ("admin", k.admin.to_string(), ua.clone()),
        (
            "protocol_fee_recipient",
            k.protocol_fee_recipient.to_string(),
            s.protocol_fee_recipient.to_string(),
        ),
        ("fee_bps", k.fee_bps.to_string(), s.fee_bps.to_string()),
        (
            "door_share_bps",
            k.door_share_bps.to_string(),
            s.door_share_bps.to_string(),
        ),
        (
            "founder_share_bps",
            k.founder_share_bps.to_string(),
            s.founder_share_bps.to_string(),
        ),
        (
            "door_fee_lamports",
            k.door_fee_lamports.to_string(),
            s.door_fee_lamports.to_string(),
        ),
        (
            "room_fee_lamports",
            k.room_fee_lamports.to_string(),
            s.room_fee_lamports.to_string(),
        ),
        (
            "convert_fee_lamports",
            k.convert_fee_lamports.to_string(),
            s.convert_fee_lamports.to_string(),
        ),
        (
            "v_sol_lamports",
            k.v_sol_lamports.to_string(),
            s.v_sol_lamports.to_string(),
        ),
        ("v_tok", k.v_tok.to_string(), s.v_tok.to_string()),
        ("supply", k.supply.to_string(), s.supply.to_string()),
        (
            "r_star_lamports",
            k.r_star_lamports.to_string(),
            s.r_star_lamports.to_string(),
        ),
        (
            "meteora_dynamic_config",
            k.meteora_dynamic_config.to_string(),
            s.meteora_dynamic_config.to_string(),
        ),
        (
            "graduation_trigger_lamports",
            k.graduation_trigger_lamports.to_string(),
            s.graduation_trigger_lamports.to_string(),
        ),
        ("paused", k.paused.to_string(), s.paused.to_string()),
        (
            "matcher_authority",
            k.matcher_authority.to_string(),
            s.matcher_authority.to_string(),
        ),
        (
            "live_min_reserve_lamports",
            k.live_min_reserve_lamports.to_string(),
            s.live_min_reserve_lamports.to_string(),
        ),
        (
            "live_max_idle_seconds",
            k.live_max_idle_seconds.to_string(),
            s.live_max_idle_seconds.to_string(),
        ),
        (
            "live_new_seconds",
            k.live_new_seconds.to_string(),
            s.live_new_seconds.to_string(),
        ),
        (
            "live_min_volume_lamports",
            k.live_min_volume_lamports.to_string(),
            s.live_min_volume_lamports.to_string(),
        ),
        (
            "pool_min_window_lp_fee",
            k.pool_min_window_lp_fee.to_string(),
            s.pool_min_window_lp_fee.to_string(),
        ),
        (
            "bump",
            k.bump.to_string(),
            Pubkey::find_program_address(&[b"config"], &ID)
                .1
                .to_string(),
        ),
    ];
    let mut mismatches = 0;
    let mut table = vec![];
    println!(
        "Config {cfg_key} at slot {slot} ({} bytes, owner {})",
        acc.data.len(),
        acc.owner
    );
    for (f, got, want) in rows {
        let ok = got == want;
        mismatches += usize::from(!ok);
        println!(
            "{f:<29} {got:<46} {want:<46} {}",
            if ok { "ok" } else { "MISMATCH" }
        );
        table.push(json!({"field": f, "on_chain": got, "expected": want, "match": ok}));
    }
    fs::write(
        out,
        serde_json::to_string_pretty(&json!({
            "config": cfg_key.to_string(), "slot": slot, "data_len": acc.data.len(),
            "owner": acc.owner.to_string(), "upgrade_authority": ua, "fields": table, "mismatches": mismatches,
        }))?,
    )?;
    if mismatches > 0 {
        bail!("{mismatches} Config fields differ from the expected settings");
    }
    Ok(())
}

#[derive(Clone)]
struct DoorKeys {
    door: Pubkey,
    mint: Pubkey,
    vault: Pubkey,
    backing: Pubkey,
}
impl DoorKeys {
    /// Door PDAs are seeded by the signed door nonce (0 for door 0), not by an index.
    fn new(room: Pubkey, nonce: u64) -> Self {
        let door = p(&[b"door", room.as_ref(), &nonce.to_le_bytes()]);
        Self {
            door,
            mint: p(&[b"door_mint", room.as_ref(), &nonce.to_le_bytes()]),
            vault: p(&[b"door_vault", door.as_ref()]),
            backing: p(&[b"door_room_vault", door.as_ref()]),
        }
    }
}
fn launch(name: &str, symbol: &str) -> Launch {
    Launch {
        name: name.into(),
        symbol: symbol.into(),
        uri: "https://example.invalid/doors-devnet-smoke.json".into(),
        first_buy_lamports: 0,
        min_tokens_out: 0,
        matcher_version: 1,
        rule: 0,
        face: 0,
        max_fee_lamports: 0,
        expected_terms_hash: [0; 32],
        door_nonce: 0,
        expires_at_slot: 0,
    }
}
/// Fill the signed launch fields that depend on chain state: the Config's launch-terms
/// hash, the door nonce, and an expiry one full launch window after the current slot.
fn prepare(c: &Chain, mut l: Launch, door_nonce: u64) -> Result<Launch> {
    let cfg = Config::try_deserialize(&mut &c.account(&p(&[b"config"]))?.data[..])?;
    l.expected_terms_hash = cfg.launch_terms_hash();
    l.door_nonce = door_nonce;
    l.expires_at_slot = c.slot()? + MAX_LAUNCH_WINDOW_SLOTS;
    Ok(l)
}
/// A random non-zero door nonce from the OS CSPRNG.
fn door_nonce() -> Result<u64> {
    loop {
        let n = random_u64()?;
        if n != 0 {
            return Ok(n);
        }
    }
}
fn create_ata_ix(payer: Pubkey, owner: Pubkey, mint: Pubkey, program: Pubkey) -> Instruction {
    Instruction {
        program_id: ATA,
        accounts: vec![
            AccountMeta::new(payer, true),
            AccountMeta::new(ata(owner, mint, program), false),
            AccountMeta::new_readonly(owner, false),
            AccountMeta::new_readonly(mint, false),
            AccountMeta::new_readonly(SYS, false),
            AccountMeta::new_readonly(program, false),
        ],
        data: vec![1], // CreateIdempotent
    }
}

struct Ctx {
    cfg: Pubkey,
    room: Pubkey,
    rid: u64,
}
impl Ctx {
    fn new(rid: u64) -> Self {
        Self {
            cfg: p(&[b"config"]),
            room: p(&[b"room", &rid.to_le_bytes()]),
            rid,
        }
    }
    fn core(&self, r: &Room) -> a::Core {
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
    fn create_ix(&self, user: Pubkey, matcher: Pubkey, l: Launch) -> Instruction {
        let d = DoorKeys::new(self.room, 0);
        let key = smoke_name_key(&l.name);
        instr(
            a::CreateRoom {
                user,
                matcher,
                config: self.cfg,
                room: self.room,
                reserve: p(&[b"reserve", self.room.as_ref()]),
                fees: p(&[b"fees", self.room.as_ref()]),
                grad_payer: p(&[b"grad_payer", self.room.as_ref()]),
                slug: p(&[b"slug", &l.identity()]),
                old_holder: None,
                name_lock: Some(p(&[b"name", &key])),
                old_name_holder: None,
                room_mint: p(&[b"room_mint", self.room.as_ref()]),
                room_vault: p(&[b"room_vault", self.room.as_ref()]),
                retired: p(&[b"retired", self.room.as_ref()]),
                fee_wsol: p(&[b"fee_wsol", self.room.as_ref()]),
                door: d.door,
                door_mint: d.mint,
                door_vault: d.vault,
                backing: d.backing,
                user_token: ata(user, d.mint, T22),
                token_program: T22,
                classic_token_program: CLASSIC,
                wsol_mint: WSOL,
                associated_token_program: ATA,
                system_program: SYS,
            },
            ix::CreateRoom {
                room_id: self.rid,
                launch: l,
                name_key: Some(key),
            },
        )
    }
    fn open_ix(&self, r: &Room, user: Pubkey, matcher: Pubkey, l: Launch) -> Instruction {
        let _ = r;
        let d = DoorKeys::new(self.room, l.door_nonce);
        instr(
            a::OpenDoor {
                user,
                matcher,
                core: self.core(r),
                slug: p(&[b"slug", &l.identity()]),
                old_holder: None,
                door: d.door,
                door_mint: d.mint,
                door_vault: d.vault,
                backing: d.backing,
                user_token: ata(user, d.mint, T22),
                token_program: T22,
                associated_token_program: ATA,
                system_program: SYS,
            },
            ix::OpenDoor { launch: l },
        )
    }
    fn trade_ix(
        &self,
        r: &Room,
        user: Pubkey,
        door: Option<&DoorKeys>,
        buy: bool,
        n: u64,
    ) -> Instruction {
        let user_token = door.map_or(ata(user, r.room_mint, T22), |d| ata(user, d.mint, T22));
        let ac = a::TradeAccounts {
            user,
            core: self.core(r),
            door: door.map(|d| d.door),
            door_mint: door.map(|d| d.mint),
            door_vault: door.map(|d| d.vault),
            backing: door.map(|d| d.backing),
            user_token,
            token_program: T22,
            system_program: SYS,
        };
        if buy {
            instr(
                ac,
                ix::Buy {
                    lamports_in: n,
                    min_tokens_out: 0,
                },
            )
        } else {
            instr(
                ac,
                ix::Sell {
                    tokens_in: n,
                    min_lamports_out: 0,
                },
            )
        }
    }
    fn convert_ix(
        &self,
        r: &Room,
        user: Pubkey,
        x: &DoorKeys,
        y: &DoorKeys,
        n: u64,
    ) -> Instruction {
        instr(
            a::Convert {
                user,
                core: self.core(r),
                door_a: x.door,
                door_b: y.door,
                mint_a: x.mint,
                mint_b: y.mint,
                vault_a: x.vault,
                vault_b: y.vault,
                backing_a: x.backing,
                backing_b: y.backing,
                user_a: ata(user, x.mint, T22),
                user_b: ata(user, y.mint, T22),
                token_program: T22,
                system_program: SYS,
            },
            ix::Convert {
                amount: n,
                max_fee_lamports: 0,
            },
        )
    }
    fn retire_ix(&self, r: &Room) -> Instruction {
        let c = self.core(r);
        let out = c.retired;
        instr(
            a::Retire {
                core: c,
                retired_output: out,
                token_program: T22,
            },
            ix::RetirePending {},
        )
    }
    fn claim_ix(
        &self,
        r: &Room,
        authority: Pubkey,
        d: &DoorKeys,
        recipient: Pubkey,
    ) -> Instruction {
        instr(
            a::Claim {
                authority,
                core: self.core(r),
                door: Some(d.door),
                door_mint: Some(d.mint),
                door_vault: Some(d.vault),
                backing: Some(d.backing),
                fee_wsol: r.fee_wsol,
                wsol_mint: WSOL,
                recipient,
                recipient_wsol: ata(recipient, WSOL, CLASSIC),
                classic_token_program: CLASSIC,
            },
            ix::ClaimDoorFees {},
        )
    }
}

/// Room nonce from the OS CSPRNG, as scripts/room_nonce.py does.
fn random_u64() -> Result<u64> {
    let mut b = [0u8; 8];
    fs::File::open("/dev/urandom")?.read_exact(&mut b)?;
    Ok(u64::from_le_bytes(b))
}

fn trades_in(rec: &Value) -> Vec<Trade> {
    rec["events"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|e| b64(e.as_str()?))
        .filter(|d| d.len() > 8 && &d[..8] == Trade::DISCRIMINATOR)
        .filter_map(|d| Trade::try_from_slice(&d[8..]).ok())
        .collect()
}
fn b64(s: &str) -> Option<Vec<u8>> {
    const A: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = vec![];
    let (mut buf, mut bits) = (0u32, 0u32);
    for ch in s.bytes().filter(|&c| c != b'=') {
        buf = (buf << 6) | A.iter().position(|&x| x == ch)? as u32;
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            out.push((buf >> bits) as u8);
        }
    }
    Some(out)
}

fn mint_check(c: &Chain, mint: &Pubkey) -> Result<Value> {
    let acc = c.account(mint)?;
    let m = StateWithExtensions::<Mint>::unpack(&acc.data)?;
    let md =
        m.get_variable_len_extension::<spl_token_metadata_interface::state::TokenMetadata>()?;
    let ua = Option::<Pubkey>::from(md.update_authority);
    let ok = m.base.supply == U
        && m.base.mint_authority.is_none()
        && m.base.freeze_authority.is_none()
        && ua.is_none()
        && acc.owner == T22;
    Ok(json!({
        "mint": mint.to_string(), "owner": acc.owner.to_string(), "supply": m.base.supply.to_string(),
        "decimals": m.base.decimals, "mint_authority": format!("{:?}", m.base.mint_authority),
        "freeze_authority": format!("{:?}", m.base.freeze_authority),
        "metadata_update_authority": format!("{ua:?}"), "name": md.name, "symbol": md.symbol,
        "extensions": format!("{:?}", m.get_extension_types()?), "ok": ok,
    }))
}

/// The matcher's NameLock key (services/matcher rules.py `name_lock_key`) for the plain ASCII names the smoke uses
/// (words of ASCII letters and digits separated by single spaces). Rules B and C rewrite no ASCII letter except '|',
/// which plain names lack, so for them the service key is rule I alone: every letter joined, lower-case, `rn`->`m`
/// then `vv`->`w`, upper-case, digits 0 1 3 4 5 7 8 -> O I E A S T B, L -> I; then repeatedly a trailing COIN,
/// TOKEN, OFFICIAI, SOIANA or CTO and a leading THE or OFFICIAI (while 4+ letters remain) are removed; class N
/// when the joined name has 4+ letters. Any other name is refused rather than keyed wrongly.
/// `smoke_key_matches_the_service` pins it to vectors computed with the service's rules.py.
fn smoke_name_key(name: &str) -> [u8; NAME_KEY_LEN] {
    const TRAIL: [&str; 5] = ["OFFICIAI", "SOIANA", "TOKEN", "COIN", "CTO"]; // longest first, as rules.py
    const LEAD: [&str; 2] = ["THE", "OFFICIAI"];
    for w in name.split(' ') {
        assert!(
            !w.is_empty() && w.bytes().all(|c| c.is_ascii_alphanumeric()),
            "plain name: {name}"
        );
    }
    let full: String = name
        .replace(' ', "")
        .to_ascii_lowercase()
        .replace("rn", "m")
        .replace("vv", "w")
        .to_ascii_uppercase()
        .chars()
        .map(|c| match c {
            '0' => 'O',
            '1' => 'I',
            '3' => 'E',
            '4' => 'A',
            '5' => 'S',
            '7' => 'T',
            '8' => 'B',
            'L' => 'I',
            c => c,
        })
        .collect();
    let mut nk = full.as_str();
    let mut changed = true;
    while changed {
        changed = false;
        for w in TRAIL {
            if nk.len() > w.len() && nk.ends_with(w) {
                nk = &nk[..nk.len() - w.len()];
                changed = true;
            }
        }
        for w in LEAD {
            if nk.len() >= w.len() + 4 && nk.starts_with(w) {
                nk = &nk[w.len()..];
                changed = true;
            }
        }
    }
    assert!(full.len() >= 4 && !nk.is_empty(), "class N name: {name}");
    let h = solana_sha256_hasher::hashv(&[b"doors-v1:name-key:v1\0N\0", nk.as_bytes()]);
    h.to_bytes()[..NAME_KEY_LEN].try_into().unwrap()
}
fn smoke_key_matches_the_service() {
    for (name, key) in [
        ("Doors Smoke 0A1B2C", "2f06537ec8ddfa6f5057dc7d33ee1237"),
        ("Doors Smoke FFE387", "10a09ffa681e7b0fc073e86e91d3f1a0"),
        ("Doors Smoke 4578BD", "40bd7fa8d5a4143caf668ae8d0b26612"),
        ("Doors Unsigned Probe", "8e6865372d9077ac15a17f18121f5953"),
        ("Doors Devnet Smoke", "ba48f6c3bcb2159df982b88647109e3d"),
        ("Turn Vvave 0137", "008fd9082274f6972df9a3b87cca37be"),
        ("Lilly Bell 71", "a25aa2268e687c6b418cc03c9e363ce2"),
        ("Bull Run Al", "0e74f7d87fe255588ea2f0f4960bb64c"),
        ("Bunker Net", "97566165cd9c36c571beecff6f3e99e4"), // rule I: rn folds across the space
        (
            "The Official Doors Coin",
            "2b0f846ca2a71d7deb83978481ee88ee",
        ),
        ("Theory CTO Coin", "1ea2e36edd691a28558e86ecf2262508"), // trailing words first: THEORY
        ("tHe rUnNeR", "973ac7359cf00f9645eec92a96407212"),      // case cannot change the key
    ] {
        let got: String = smoke_name_key(name)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        assert_eq!(
            got, key,
            "smoke name key differs from the service's for {name}"
        );
    }
}
fn smoke(dir: &str, out: &str) -> Result<()> {
    smoke_key_matches_the_service();
    let mut c = Chain::new();
    let launcher = key(dir, "smoke-launcher")?;
    let trader = key(dir, "smoke-trader")?;
    let matcher = key(dir, "matcher-authority")?;
    let rid = random_u64()?;
    let ctx = Ctx::new(rid);
    let (lk, tk) = (launcher.pubkey(), trader.pubkey());
    let n1 = door_nonce()?;
    let d0 = DoorKeys::new(ctx.room, 0);
    let d1 = DoorKeys::new(ctx.room, n1);
    // A fresh identity per run: on a persistent cluster (devnet) an earlier run's room still holds the
    // previous identity's SlugLock, so a fixed name would need its old holder (Holder, 6013).
    let tag = format!("{:06X}", rid & 0xFF_FFFF);
    let (name, symbol) = (format!("Doors Smoke {tag}"), format!("D{}", &tag[..5]));
    let (name, symbol) = (name.as_str(), symbol.as_str());

    // 1. create_room, signed by the launcher and the matcher; creates door 0.
    let l0 = prepare(&c, launch(name, symbol), 0)?;
    c.send(
        "create_room",
        &[ctx.create_ix(lk, matcher.pubkey(), l0)],
        &launcher,
        &[&matcher],
    )?;
    let r = c.room(&ctx.room)?;
    // Token accounts that later trades expect (idempotent ATA creation, as clients do).
    c.send(
        "create_atas_launcher",
        &[
            create_ata_ix(lk, lk, d0.mint, T22),
            create_ata_ix(lk, lk, r.room_mint, T22),
            create_ata_ix(lk, lk, WSOL, CLASSIC),
        ],
        &launcher,
        &[],
    )?;
    // 2. open_door into the room from a second wallet, same identity (a vamp joining).
    let l1 = prepare(&c, launch(name, symbol), n1)?;
    c.send(
        "open_door",
        &[ctx.open_ix(&r, tk, matcher.pubkey(), l1)],
        &trader,
        &[&matcher],
    )?;
    c.send(
        "create_atas_trader",
        &[
            create_ata_ix(tk, tk, d1.mint, T22),
            create_ata_ix(tk, tk, r.room_mint, T22),
            create_ata_ix(tk, tk, WSOL, CLASSIC),
            create_ata_ix(tk, lk, d1.mint, T22),
        ],
        &trader,
        &[],
    )?;
    // 3. a buy through door 0, a buy through door 1, a sell, a convert.
    let r = c.room(&ctx.room)?;
    let mut fee_recs = vec![];
    fee_recs.push((
        "door0",
        c.send(
            "buy_door0",
            &[ctx.trade_ix(&r, lk, Some(&d0), true, 100_000_000)],
            &launcher,
            &[],
        )?,
    ));
    fee_recs.push((
        "door1",
        c.send(
            "buy_door1",
            &[ctx.trade_ix(&r, tk, Some(&d1), true, 100_000_000)],
            &trader,
            &[],
        )?,
    ));
    let held = c.balance(&ata(lk, d0.mint, T22))?;
    fee_recs.push((
        "door0",
        c.send(
            "sell_door0",
            &[ctx.trade_ix(&r, lk, Some(&d0), false, held / 2)],
            &launcher,
            &[],
        )?,
    ));
    let held = c.balance(&ata(lk, d0.mint, T22))?;
    c.send(
        "convert_door0_to_door1",
        &[ctx.convert_ix(&r, lk, &d0, &d1, held / 2)],
        &launcher,
        &[],
    )?;
    // 4. a direct buy of the room token.
    fee_recs.push((
        "room",
        c.send(
            "buy_room_token",
            &[ctx.trade_ix(&r, tk, None, true, 50_000_000)],
            &trader,
            &[],
        )?,
    ));

    // Fee split, checked before retire/claim move the counters: expected values come from
    // each Trade event's fee and the room's snapshotted door/founder shares.
    let rr = c.room(&ctx.room)?;
    let (dd0, dd1) = (c.door(&d0.door)?, c.door(&d1.door)?);
    let (mut e_d0, mut e_d1, mut e_pending, mut e_protocol, mut e_founder, mut e_total) =
        (0u64, 0u64, 0u64, 0u64, 0u64, 0u64);
    let mut trade_rows = vec![];
    for (route, rec) in &fee_recs {
        for t in trades_in(rec) {
            let door_part = (t.fee as u128 * rr.door_share_bps as u128 / 10_000) as u64;
            let founder_part = (t.fee as u128 * rr.founder_share_bps as u128 / 10_000) as u64;
            let protocol_part = t.fee - door_part - founder_part;
            match *route {
                "door0" => e_d0 += door_part,
                "door1" => e_d1 += door_part,
                _ => e_pending += door_part,
            }
            e_protocol += protocol_part;
            e_founder += founder_part;
            e_total += t.fee;
            trade_rows.push(json!({
                "tx": rec["name"], "route": route, "buy": t.buy, "tokens": t.tokens.to_string(),
                "curve_lamports": t.curve_lamports, "fee": t.fee, "door_or_reserve_share": door_part,
                "protocol_share": protocol_part, "founder_share": founder_part,
            }));
        }
    }
    let expected = json!({"door0": e_d0, "door1": e_d1, "pending_reserve": e_pending, "protocol": e_protocol, "founder": e_founder, "fee_total": e_total});
    let on_chain = json!({
        "door0": dd0.accrued_sol, "door1": dd1.accrued_sol, "pending_reserve": rr.pending_reserve_sol,
        "protocol": rr.protocol_accrued_sol, "founder": rr.founder_accrued,
        "fee_total": dd0.accrued_sol + dd1.accrued_sol + rr.pending_reserve_sol + rr.protocol_accrued_sol + rr.founder_accrued,
    });
    let rent0 = c.rent(0)?;
    let fee_vault = c.account(&p(&[b"fees", ctx.room.as_ref()]))?.lamports;

    // 5. retire_pending; 6. claim_door_fees for door 0 by its fee recipient (the launcher).
    c.send("retire_pending", &[ctx.retire_ix(&rr)], &launcher, &[])?;
    let after_retire = c.room(&ctx.room)?;
    c.send(
        "claim_door_fees",
        &[ctx.claim_ix(&after_retire, lk, &d0, lk)],
        &launcher,
        &[],
    )?;
    let d0_after = c.door(&d0.door)?;

    // On-chain state against the spec.
    let rf = c.room(&ctx.room)?;
    let reserve_vault = c.account(&p(&[b"reserve", ctx.room.as_ref()]))?.lamports;
    let integral = rf.curve(rf.sold).map_err(|e| anyhow!("{e:?}"))?;
    let room_vault = c.balance(&rf.room_vault)?;
    let mut doors = vec![];
    for d in [&d0, &d1] {
        let door = c.door(&d.door)?;
        let vault = c.balance(&d.vault)?;
        let backing = c.balance(&d.backing)?;
        let circulating = U - vault;
        doors.push(json!({
            "door": d.door.to_string(), "index": door.index, "mint": mint_check(&c, &d.mint)?,
            "door_vault_balance": vault.to_string(), "circulating_door_supply": circulating.to_string(),
            "room_token_backing_vault_balance": backing.to_string(), "door.backing": door.backing.to_string(),
            "backing_covers_circulating": backing >= circulating, "backing_exactly_equals_circulating": backing == circulating,
            "creator": door.creator.to_string(), "fee_recipient": door.fee_recipient.to_string(),
            "accrued_sol": door.accrued_sol, "claimed_sol": door.claimed_sol,
        }));
    }
    let name_key = smoke_name_key(name);
    let name_lock = p(&[b"name", &name_key]);
    let nl = NameLock::try_deserialize(&mut &c.account(&name_lock)?.data[..])?;
    let verify = json!({
        "room": ctx.room.to_string(), "room_id": rid.to_string(), "door1_nonce": n1.to_string(),
        "name_lock": {"address": name_lock.to_string(), "key": name_key.iter().map(|b| format!("{b:02x}")).collect::<String>(),
                      "room_id": nl.room_id.to_string(), "ok": nl.room_id == rid && nl.key == name_key},
        "status": rf.status, "door_count": rf.door_count,
        "room_mint": mint_check(&c, &rf.room_mint)?, "doors": doors,
        "reserve": rf.reserve.to_string(), "sold": rf.sold.to_string(), "retired": rf.retired.to_string(),
        "room_vault_balance": room_vault.to_string(), "room_vault_covers_unsold": room_vault >= U - rf.sold,
        "curve_integral_of_sold": integral.to_string(), "reserve_covers_curve_integral": rf.reserve >= integral,
        "reserve_vault_lamports": reserve_vault.to_string(), "zero_data_rent": rent0,
        "reserve_vault_covers_reserve": reserve_vault - rent0 >= rf.reserve,
        "fee_split": {
            "expected_from_trade_events": expected, "on_chain_counters_before_retire_and_claim": on_chain,
            "match": expected == on_chain, "trades": trade_rows,
            "fee_vault_lamports_before_retire": fee_vault, "fee_vault_covers_counters": fee_vault - rent0 >= e_total,
        },
        "after_retire": {
            "pending_reserve_sol": after_retire.pending_reserve_sol, "reserve": after_retire.reserve.to_string(),
            "retired": after_retire.retired.to_string(), "reserve_increase": (after_retire.reserve - rr.reserve).to_string(),
        },
        "after_claim": {"door0_accrued_sol": d0_after.accrued_sol, "door0_claimed_sol": d0_after.claimed_sol},
    });
    fs::write(
        out,
        serde_json::to_string_pretty(&json!({
            "program": ID.to_string(), "launcher": lk.to_string(), "trader": tk.to_string(),
            "matcher": matcher.pubkey().to_string(), "transactions": c.log, "verify": verify,
        }))?,
    )?;
    println!("{}", serde_json::to_string_pretty(&verify)?);
    Ok(())
}

fn fail(dir: &str, smoke_report: &str, out: &str) -> Result<()> {
    let mut c = Chain::new();
    let launcher = key(dir, "smoke-launcher")?;
    let trader = key(dir, "smoke-trader")?;
    let matcher = key(dir, "matcher-authority")?;
    let s: Value = serde_json::from_str(&fs::read_to_string(smoke_report)?)?;
    let rid: u64 = s["verify"]["room_id"]
        .as_str()
        .ok_or_else(|| anyhow!("room_id"))?
        .parse()?;
    let ctx = Ctx::new(rid);
    let r = c.room(&ctx.room)?;
    let (lk, tk) = (launcher.pubkey(), trader.pubkey());
    let n1: u64 = s["verify"]["door1_nonce"]
        .as_str()
        .ok_or_else(|| anyhow!("door1_nonce"))?
        .parse()?;
    let d0 = DoorKeys::new(ctx.room, 0);
    let d1 = DoorKeys::new(ctx.room, n1);
    // A fresh room for the create_room cases, so the signature is the only defect.
    let ctx2 = Ctx::new(random_u64()?);
    let probe = prepare(&c, launch("Doors Unsigned Probe", "PROBE"), 0)?;
    let smoke_launch = prepare(&c, launch("Doors Devnet Smoke", "DOORS"), door_nonce()?)?;
    let matcher_index = 1; // `matcher` is the second account of both CreateRoom and OpenDoor

    // (a) No matcher signature: the matcher account is present but not marked as a signer.
    let mut ixn = ctx2.create_ix(lk, matcher.pubkey(), probe.clone());
    assert_eq!(ixn.accounts[matcher_index].pubkey, matcher.pubkey());
    ixn.accounts[matcher_index].is_signer = false;
    let t = c.tx(&[ixn], &launcher, &[])?;
    c.send_fail("create_room_without_matcher_signature", t)?;
    let mut ixn = ctx.open_ix(&r, tk, matcher.pubkey(), smoke_launch.clone());
    assert_eq!(ixn.accounts[matcher_index].pubkey, matcher.pubkey());
    ixn.accounts[matcher_index].is_signer = false;
    let t = c.tx(&[ixn], &trader, &[])?;
    c.send_fail("open_door_without_matcher_signature", t)?;

    // (b) The matcher signed one routing decision; the submitted transaction carries different
    // routing data with the matcher's signature grafted on. The payer re-signs the new message.
    let mut open_changed = smoke_launch.clone();
    open_changed.rule = 3;
    // Routing fields only (rule/face): changing name or symbol would also change the
    // SlugLock PDA, and the forgery must keep the signed account list identical.
    let mut create_changed = probe.clone();
    create_changed.rule = 2;
    create_changed.face = 7;
    let cases = [
        (
            "create_room_signature_over_different_routing_data",
            ctx2.create_ix(lk, matcher.pubkey(), probe.clone()),
            ctx2.create_ix(lk, matcher.pubkey(), create_changed),
            &launcher,
        ),
        (
            "open_door_signature_over_different_routing_data",
            ctx.open_ix(&r, tk, matcher.pubkey(), smoke_launch.clone()),
            ctx.open_ix(&r, tk, matcher.pubkey(), open_changed),
            &trader,
        ),
    ];
    for (name, signed_ix, submitted_ix, payer) in cases {
        let signed = c.tx(&[signed_ix], payer, &[&matcher])?;
        let mut forged = signed.clone();
        forged.message = Message::new_with_blockhash(
            &[
                ComputeBudgetInstruction::set_compute_unit_limit(CU_LIMIT),
                submitted_ix,
            ],
            Some(&payer.pubkey()),
            &signed.message.recent_blockhash,
        );
        assert_eq!(forged.message.account_keys, signed.message.account_keys);
        let pi = forged
            .message
            .account_keys
            .iter()
            .position(|k| *k == payer.pubkey())
            .unwrap();
        forged.signatures[pi] = payer.sign_message(&forged.message_data());
        c.send_fail_with(name, forged, false)?;
    }

    // (c) A sell larger than the seller's balance.
    let held = c.balance(&ata(tk, d1.mint, T22))?;
    let t = c.tx(
        &[ctx.trade_ix(&r, tk, Some(&d1), false, held + 1)],
        &trader,
        &[],
    )?;
    c.send_fail("sell_exceeding_balance", t)?;

    // (d) claim_door_fees for door 0 signed by the trader, who is not door 0's fee recipient.
    let t = c.tx(&[ctx.claim_ix(&r, tk, &d0, tk)], &trader, &[])?;
    c.send_fail("claim_door_fees_by_non_recipient", t)?;

    fs::write(
        out,
        serde_json::to_string_pretty(
            &json!({"program": ID.to_string(), "room": ctx.room.to_string(), "probe_room": ctx2.room.to_string(), "cases": c.log}),
        )?,
    )?;
    for r in &c.log {
        println!(
            "{}: landed={} sig={} error={} rpc_error={} log={}",
            r["name"], r["landed"], r["signature"], r["error"], r["rpc_error"], r["error_log"]
        );
    }
    Ok(())
}

/// Offline-safe checks: base64 round trip, and devnet parses our wire format
/// (simulating an unfunded payer must fail on funds, not on deserialisation).
fn selftest(dir: &str) -> Result<()> {
    let sample: Vec<u8> = (0u16..=600).map(|i| (i * 7 % 256) as u8).collect();
    for n in 0..5 {
        assert_eq!(
            b64(&b64_encode(&sample[n..])).unwrap(),
            sample[n..].to_vec()
        );
    }
    let c = Chain::new();
    let payer = key(dir, "smoke-launcher")?;
    let ixn = Instruction {
        program_id: SYS,
        accounts: vec![
            AccountMeta::new(payer.pubkey(), true),
            AccountMeta::new(payer.pubkey(), false),
        ],
        data: vec![2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    };
    let t = c.tx(&[ixn], &payer, &[])?;
    let wire = b64_encode(&bincode::serialize(&t)?);
    let r = c.rpc(
        "simulateTransaction",
        json!([wire, {"encoding": "base64", "sigVerify": true, "commitment": "confirmed"}]),
    )?;
    println!(
        "simulate (expected to fail on funds, not parsing): {}",
        r["value"]["err"]
    );
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let arg = |i: usize| {
        args.get(i)
            .map(String::as_str)
            .ok_or_else(|| anyhow!("missing argument {i}"))
    };
    match args.get(1).map(String::as_str) {
        Some("init") => init(arg(2)?, arg(3)?, arg(4)?),
        Some("config") => config(arg(2)?, arg(3)?),
        Some("smoke") => smoke(arg(2)?, arg(3)?),
        Some("fail") => fail(arg(2)?, arg(3)?, arg(4)?),
        Some("selftest") => selftest(arg(2)?),
        _ => bail!("usage: doors-devnet init|config|smoke|fail ..."),
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn smoke_name_key_equals_the_service_vectors() {
        super::smoke_key_matches_the_service();
    }
}
