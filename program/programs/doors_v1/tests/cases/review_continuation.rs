// Review continuation (item 2 onwards). Real SBF execution only; amounts are lamports and token base units.

fn review_evidence(name: &str, data: Value) {
    println!("REVIEW_CONTINUATION {data}");
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(format!("../../verification/review_{name}.json"));
    std::fs::write(path, serde_json::to_string_pretty(&data).unwrap() + "\n").unwrap();
}

fn lamports_of(f: &Fixture, who: &Pubkey) -> u64 {
    f.svm.get_account(who).unwrap().lamports
}

/// Opens a door with a first buy, optionally after a front-running room buy by another wallet that sells right
/// after. Returns (accepted, victim door tokens, victim exit lamports, attacker net lamports).
fn door_open_sandwich_limit(front: u64, min_out: u64, max_reserve_lamports: u64) -> (bool, u64, u64, i128) {
    const FIRST_BUY: u64 = 1_010_000_000;
    let mut f = Fixture::new(0);
    // A bystander gives the room 10 SOL of depth first, as an established narrative would have.
    let mut seed = Keypair::new_from_array([72; 32]);
    f.svm.airdrop(&seed.pubkey(), 50_000_000_000).unwrap();
    paired_actor(&mut f, &mut seed);
    f.make_ata(f.r().room_mint, spl_token_2022_interface::ID);
    f.trade(None, true, 10_100_000_000);
    paired_actor(&mut f, &mut seed);

    let mut attacker = Keypair::new_from_array([71; 32]);
    f.svm.airdrop(&attacker.pubkey(), 500_000_000_000).unwrap();
    let attacker_key = attacker.pubkey();
    let attacker_start = lamports_of(&f, &attacker_key);
    if front > 0 {
        paired_actor(&mut f, &mut attacker);
        f.make_ata(f.r().room_mint, spl_token_2022_interface::ID);
        f.trade(None, true, front);
        paired_actor(&mut f, &mut attacker);
    }

    let mut l = launch("First room");
    l.symbol = "COPY".into();
    l.first_buy_lamports = FIRST_BUY;
    l.min_tokens_out = min_out;
    l.max_reserve_lamports = max_reserve_lamports;
    let l = f.fill(l, true); // fix the door nonce once, before the room's door counter moves
    let accepted = {
        let ix = f.open_ix(l.clone(), None);
        let tx = Transaction::new(
            &[&f.user, &f.matcher],
            Message::new(
                &[ComputeBudgetInstruction::set_compute_unit_limit(1_400_000), ix],
                Some(&f.user.pubkey()),
            ),
            f.svm.latest_blockhash(),
        );
        let ok = f.svm.send_transaction(tx).is_ok();
        if ok {
            let d = DoorKeys::new(f.room, l.door_nonce, f.user.pubkey());
            f.doors.push(d);
        }
        ok
    };
    if !accepted {
        return (false, 0, 0, 0);
    }
    let victim_door = f.doors.len() - 1;
    let victim_tokens = f.balance(f.doors[victim_door].user);

    if front > 0 {
        paired_actor(&mut f, &mut attacker);
        let room_ata = ata(f.user.pubkey(), f.r().room_mint, spl_token_2022_interface::ID);
        let held = f.balance(room_ata);
        f.trade(None, false, held);
        paired_actor(&mut f, &mut attacker);
    }
    let attacker_net = i128::from(lamports_of(&f, &attacker_key)) - i128::from(attacker_start);

    let before = lamports_of(&f, &f.user.pubkey());
    f.trade(Some(victim_door), false, victim_tokens);
    let victim_exit = lamports_of(&f, &f.user.pubkey()) - before;
    f.audit();
    (true, victim_tokens, victim_exit, attacker_net)
}

fn door_open_sandwich(front: u64, min_out: u64) -> (bool, u64, u64, i128) {
    door_open_sandwich_limit(front, min_out, 0)
}

#[test]
fn review_room_reserve_limit_refuses_front_run_and_zero_accepts() {
    let mut f = Fixture::new(0);
    f.trade(None, true, 10_100_000_000);
    let room = f.r();
    let v_sol = u128::from(room.v_sol_lamports);
    let virtual_reserve = v_sol + u128::from(room.reserve);
    let limit = u64::try_from((virtual_reserve.pow(2) * 10_200 / 10_000).isqrt() - v_sol).unwrap();
    let (ok, quote, _, _) = door_open_sandwich(0, 1);
    assert!(ok);
    for front in [5_000_000_000, 20_000_000_000, 60_000_000_000] {
        assert!(!door_open_sandwich_limit(front, quote * 98 / 100, limit).0);
        assert!(door_open_sandwich_limit(front, quote * 98 / 100, 0).0);
    }
    assert!(door_open_sandwich_limit(0, quote * 98 / 100, limit).0);
    // Creation compares its zero birth reserve before executing the first buy.
    let mut empty = Fixture::empty(0);
    let mut l = launch("Reserve bounded creation");
    l.max_reserve_lamports = 1;
    l.first_buy_lamports = 1_010_000_000;
    empty.create(l, None);
    assert_eq!(empty.r().reserve, 1_000_000_000);
}

#[test]
fn review_same_slot_name_lock_allows_exactly_one_create() {
    let mut f = Fixture::empty(0);
    let first = launch("Same slot narrative");
    let name_key = Fixture::name_key(&first);
    let clock = f.svm.get_sysvar::<Clock>();
    f.create(first, None);
    let winner = f.room;
    f.rid += 1;
    f.room = p(&[b"room", &f.rid.to_le_bytes()]);
    f.doors.clear();
    let mut second = launch("Same slot narrative");
    second.symbol = "OTHER".into(); // different SlugLock: only NameLock prevents this race
    // The second request was signed from the same pre-create snapshot, which
    // supplied no former name holder. Do not let the fixture refresh that account.
    let ix = f.create_ix_named(second, None, Some(name_key),
        Some(p(&[b"name", &name_key])), None);
    f.fail_error(ix, true, Some("Holder"));
    assert_eq!(f.svm.get_sysvar::<Clock>().slot, clock.slot);
    assert_eq!(f.name_holder(&name_key), Some(winner));
    assert!(f.svm.get_account(&f.room).is_none());
}

fn review_resource_send(f: &mut Fixture, ix: Instruction, name: &str) -> Value {
    f.svm.expire_blockhash();
    let tx = Transaction::new(&[&f.user], Message::new(&[
        ComputeBudgetInstruction::set_compute_unit_limit(400_000),
        ComputeBudgetInstruction::set_compute_unit_price(1),
        ComputeBudgetInstruction::request_heap_frame(32_768), ix,
    ], Some(&f.user.pubkey())), f.svm.latest_blockhash());
    let meta = f.svm.send_transaction(tx).expect("bounded exit/claim must execute");
    let trace = meta.logs.iter().filter(|l| l.contains(" invoke [")).count();
    assert!(trace <= 64 && meta.compute_units_consumed < 400_000);
    f.audit();
    json!({"instruction":name,"transaction_cu":meta.compute_units_consumed,"trace_entries":trace})
}

#[test]
fn review_trades_and_claims_fit_resources_and_all_doors_exit() {
    let mut rows = vec![];
    for depth in [1, 80] {
        for prefunded in [false, true] {
            let mut f = Fixture::new(0);
            f.trade(Some(0), true, depth * 1_010_000_000);
            // Account size and number of doors do not enter a trading instruction's
            // account list. Exercise late doors with maximum metadata nonetheless.
            for i in 1..=32 {
                let mut l = launch(&format!("Limit door {i:02}{}", "x".repeat(19)));
                l.name.truncate(32);
                l.symbol = "S".repeat(10);
                l.uri = "u".repeat(200);
                f.open(l);
            }
            f.trade(None, true, 1_010_000); // nonzero settlement path on next buy
            let ix = f.trade_ix(Some(32), true, 101_000_000, 0);
            rows.push(review_resource_send(&mut f, ix, "buy_door"));
            let vault = p(&[b"swap_fees", f.room.as_ref()]);
            if prefunded { f.svm.airdrop(&vault, f.svm.minimum_balance_for_rent_exemption(0)).unwrap(); }
            let ix = f.swap_ix(0, 32, f.balance(f.doors[0].user) / 2);
            rows.push(review_resource_send(&mut f, ix, "swap_doors_lazy_vault"));
            let ix = f.swap_ix(32, 1, f.balance(f.doors[32].user) / 2);
            rows.push(review_resource_send(&mut f, ix, "swap_doors_existing_vault"));
            // Give every other late door both a redeemable position and a
            // nonzero swap-fee credit before exercising its exit and claim.
            for i in 2..32 {
                f.swap(0, i, f.balance(f.doors[0].user) / 64);
            }
            // The source door earns its own receiving-door credit as well.
            f.swap(1, 0, f.balance(f.doors[1].user) / 64);
            for i in 0..f.doors.len() {
                let held = f.balance(f.doors[i].user);
                assert!(held > 0 && f.d(i).accrued_room > 0);
                if held > 0 {
                    let ix = f.trade_ix(Some(i), false, held, 0);
                    rows.push(review_resource_send(&mut f, ix, "sell_door"));
                    assert_eq!(f.balance(f.doors[i].user), 0);
                }
                let ix = f.claim_swap_ix(Some(i));
                rows.push(review_resource_send(&mut f, ix, "claim_door_swap_fees"));
                assert_eq!(f.d(i).accrued_room, 0);
            }
            let ix = f.claim_swap_ix(None);
            rows.push(review_resource_send(&mut f, ix, "claim_protocol_swap_fees"));
            assert_eq!(f.r().swap_fees_unclaimed, 0);
        }
    }
    review_evidence("resources", json!({"depths_sol":[1,80],"doors_per_room":33,
        "metadata_bytes":[32,10,200],"rows":rows}));
}

#[test]
fn review_default_liveness_cost_self_owned_door() {
    // Ordinary attacker controls its door's fee recipient, never the protocol.
    let mut f = Fixture::new(0);
    let settings = defaults(f.matcher.pubkey(), f.matcher.pubkey());
    f.send(instr(a::UpdateConfig {admin:f.user.pubkey(),config:f.cfg},
        ix::UpdateConfig {settings,new_admin:f.user.pubkey()}), false,"separate_protocol");
    f.trade(Some(0), true, 505_000_000); // 0.5 SOL recoverable floor
    let floor_tokens = f.balance(f.doors[0].user);
    // Bootstrap the first rolling window before the one-hour grace ends.
    // This one-off volume is excluded from ongoing cost below.
    f.trade(Some(0), true, 2_272_500_000);
    f.trade(Some(0), false, f.balance(f.doors[0].user) - floor_tokens);
    f.claim(0, 0);
    let cfg = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    let protocol_before = f.r().protocol_accrued_sol;
    let wallet_before = lamports_of(&f, &f.user.pubkey());
    let mut volume = 0u128;
    // Four trades/day, spaced at the maximum allowed six-hour interval.
    // Hold the floor position; alternate 1.25 SOL net buys and matching sells.
    let mut incremental = 0;
    for step in 0..8 {
        f.time(21_600);
        assert!(f.r().live(&cfg, f.svm.get_sysvar::<Clock>().unix_timestamp).unwrap());
        let before_volume = f.r().volume_gross;
        if step % 2 == 0 {
            let before = f.balance(f.doors[0].user);
            f.trade(Some(0), true, 1_262_500_000);
            incremental = f.balance(f.doors[0].user) - before;
        } else {
            if step % 4 == 3 {
                let tx = Transaction::new(&[&f.user], Message::new(&[
                    ComputeBudgetInstruction::set_compute_unit_limit(400_000),
                    f.trade_ix(Some(0), false, incremental, 0),
                    f.claim_ix(0, 0, f.user.pubkey()),
                ], Some(&f.user.pubkey())), f.svm.latest_blockhash());
                f.svm.send_transaction(tx).unwrap();
                f.audit();
                assert_eq!(f.d(0).accrued_sol, 0);
            } else {
                f.trade(Some(0), false, incremental);
            }
        }
        volume += f.r().volume_gross - before_volume;
        if step >= 3 {
            assert!(f.r().live(&cfg, f.svm.get_sysvar::<Clock>().unix_timestamp).unwrap());
        }
        assert!(f.r().reserve >= 500_000_000);
    }
    let spent = wallet_before - lamports_of(&f, &f.user.pubkey());
    let protocol = f.r().protocol_accrued_sol - protocol_before;
    assert_eq!(spent, protocol + 40_000);
    review_evidence("liveness_cost", json!({"days":2,"volume_lamports":volume.to_string(),
        "protocol_fees_lamports":protocol,
        "wallet_cost_with_bundled_claims_lamports":spent,"trade_transactions":8,
        "claim_instructions_bundled":2,"minimum_network_fee_per_day_bundled_lamports":20000,
        "minimum_daily_cost_lamports":protocol/2+20000,
        "minimum_100_rooms_daily_cost_lamports":(protocol/2+20000)*100,
        "recoverable_floor_per_room_lamports":500_000_000u64}));
}

#[test]
fn review_door_open_room_front_run_versus_min_tokens_out() {
    // Baseline: no front-run. The service's default minimum is the snapshot quote less 2%.
    let (ok, quote, base_exit, _) = door_open_sandwich(0, 1);
    assert!(ok);
    let min_out = quote - quote / 50;
    let mut rows = vec![];
    for front in [5_000_000_000u64, 20_000_000_000, 60_000_000_000] {
        let (accepted, tokens, exit, attacker) = door_open_sandwich(front, min_out);
        rows.push(json!({
            "front_run_buy_lamports": front, "accepted_by_min_tokens_out": accepted,
            "victim_door_tokens": tokens, "victim_door_tokens_vs_quote_bps":
                if accepted { (i128::from(tokens) - i128::from(quote)) * 10_000 / i128::from(quote) } else { 0 },
            "victim_exit_lamports": exit, "victim_loss_vs_baseline_lamports":
                if accepted { i128::from(base_exit) - i128::from(exit) } else { 0 },
            "attacker_net_lamports": attacker
        }));
    }
    review_evidence(
        "door_open_front_run",
        json!({
            "case": "room buy just before open_door, sold just after; victim's min_tokens_out = quote - 2%",
            "first_buy_lamports": 1_010_000_000u64, "room_seed_lamports": 10_100_000_000u64,
            "baseline_door_tokens": quote, "baseline_exit_lamports": base_exit, "min_tokens_out": min_out,
            "runs": rows
        }),
    );
}

#[test]
fn reserve_price_relation_covers_validated_curve_extremes() {
    let f = Fixture::new(0);
    let mut r = f.r();
    let default = defaults(f.matcher.pubkey(), f.user.pubkey());
    for (vs, vt, cap) in [
        (default.v_sol_lamports, default.v_tok, default.graduation_trigger_lamports),
        (1, U + 1, NORMAL_GRADUATION_CEILING),
        (1 << 63, U + 1, 1_000_000),
        (u64::MAX, U + 1, 1_000_000),
        (u64::MAX, u64::MAX, NORMAL_GRADUATION_CEILING),
    ] {
        let mut settings = default.clone();
        settings.v_sol_lamports = vs;
        settings.v_tok = vt;
        settings.r_star_lamports = 1;
        settings.graduation_trigger_lamports = cap;
        settings.validate().unwrap();
        r.v_sol_lamports = vs;
        r.v_tok = vt;
        r.sold = 0;
        let mut previous = r.price().unwrap();
        for step in 0..=1024 {
            let reserve = cap * step / 1024;
            r.sold = doors_v1::math::inverse(vs, vt, reserve).unwrap();
            let price = r.price().unwrap();
            // The rounded inverse can hold sold constant as reserve rises.
            assert_eq!(price.numerator, previous.numerator);
            assert!(price.denominator <= previous.denominator);
            previous = price;
        }
    }
    // The exact sold-based spot can have plateaus, unlike the nominal reserve formula.
    let sold = |reserve| doors_v1::math::inverse(1 << 63, U + 1, reserve).unwrap();
    assert_eq!(sold(1), sold(2));
}

#[test]
fn legacy_price_bound_launches_are_rejected_by_the_compact_entrypoints() {
    let mut f = Fixture::empty(0);
    let old_wire = |mut ix: Instruction, name: &[u8], suffix: usize| {
        let old = solana_sha256_hasher::hashv(&[name]).to_bytes();
        ix.data[..8].copy_from_slice(&old[..8]);
        let price_end = ix.data.len() - suffix;
        ix.data.splice(price_end..price_end, [0; 8]);
        ix
    };
    let l = launch("Wire version root");
    let create = old_wire(f.create_ix(l.clone(), None), b"global:create_room", 17);
    f.fail_error(create, true, Some("InstructionFallbackNotFound"));
    assert!(f.svm.get_account(&f.room).is_none());
    f.create(l, None);
    let l = launch("Wire version door");
    let open = old_wire(f.open_ix(l.clone(), None), b"global:open_door", 0);
    f.fail_error(open, true, Some("InstructionFallbackNotFound"));
    assert_eq!(f.r().door_count, 1);
    f.open(l);
}

#[test]
fn owner_lazy_birth_accounts_and_exact_sparse_liveness() {
    let mut f = Fixture::new(0);
    assert_eq!(f.svm.get_account(&f.room).unwrap().data.len(),Room::BIRTH_LEN);
    for key in [f.r().retired_vault,f.r().fee_wsol,f.doors[0].backing,
        p(&[b"reserve",f.room.as_ref()]),p(&[b"fees",f.room.as_ref()]),p(&[b"grad_payer",f.room.as_ref()])] {
        assert!(f.svm.get_account(&key).is_none());
    }
    f.trade(Some(0),true,1_010_000_000);
    assert_eq!(f.svm.get_account(&f.room).unwrap().data.len(),Room::LEN);
    assert_eq!(f.r().liveness_buckets.len(),1);
    assert!(f.balance(f.doors[0].backing)>0);
    assert!(f.svm.get_account(&f.r().retired_vault).is_none());
    assert!(f.svm.get_account(&f.r().fee_wsol).is_none());
    f.claim(0,0);
    assert!(f.svm.get_account(&f.r().fee_wsol).is_some());
    f.trade(None,true,1_010_000_000);
    f.retire();
    assert!(f.r().retired>0 && f.balance(f.r().retired_vault)>0);
    let mut r = f.r();
    r.liveness_buckets.clear();
    let mut old = [Bucket::default();25];
    let cfg = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    for i in 0..1000u64 {
        let now = 1_800_000_000 + ((i*7919)%400_000) as i64;
        let gross = if i%7 == 0 {u64::MAX} else {i*9_999_991};
        r.record(now,gross).unwrap();
        let start=now/3600*3600;
        let b=&mut old[(start/3600%25) as usize];
        if b.start!=start {*b=Bucket {start,amount:0};}
        b.amount+=gross as u128;
        assert!(r.liveness_buckets.len()<=25);
        for clock in [now,now+3600,now+86400,now-3600] {
            assert_eq!(r.live(&cfg,clock).unwrap(),live_rule(r.status,r.created_at,r.last_trade_at,r.reserve,old.iter().copied(),&cfg,clock).unwrap());
        }
        for b in &r.liveness_buckets {let o=old[(b.start/3600%25) as usize];assert_eq!((b.start,b.amount),(o.start,o.amount));}
    }
}


#[test]
fn priority_priced_launch_metadata_packet_budgets_match_service() {
    use solana_message::{v0, AddressLookupTableAccount, VersionedMessage};

    const PACKET_LIMIT: usize = 1232;
    let f = Fixture::new(0);
    let old = p(&[b"packet-old-holder"]);
    let other = p(&[b"packet-other-holder"]);
    let key = [9; NAME_KEY_LEN];
    let lock = p(&[b"name", &key]);
    let static_table = AddressLookupTableAccount {
        key: p(&[b"packet-lookup-table"]),
        addresses: vec![
            f.cfg,
            spl_token_2022_interface::ID,
            spl_token_interface::ID,
            spl_token_interface::native_mint::ID,
            ATA,
            anchor_lang::system_program::ID,
        ],
    };
    let payer = f.user.pubkey();
    let hash = f.svm.latest_blockhash();
    let mut rows = BTreeMap::new();
    for (shape, is_create, slug_holder, name_holder, legacy, v0) in [
        ("create_room", true, None, None, 85, 235),
        ("create_room_takeover", true, Some(old), None, 53, 203),
        ("open_door", false, None, None, 276, 364),
        ("open_door_takeover", false, Some(old), None, 244, 332),
        ("create_room_name_takeover", true, None, Some(old), 53, 203),
        ("create_room_both_takeovers", true, Some(old), Some(other), 21, 171),
    ] {
        let wire_bytes = |metadata_bytes: usize, versioned: bool| {
            // Two one-byte fields plus a synthetic URI isolate the packet envelope
            // from the program's independent 32/10/200 metadata validation.
            let mut l = launch("N");
            l.symbol = "S".into();
            l.uri = "u".repeat(metadata_bytes - 2);
            l.first_buy_lamports = 1_010_000_000;
            let ix = if is_create {
                f.create_ix_named(l, slug_holder, Some(key), Some(lock), name_holder)
            } else {
                f.open_ix(l, slug_holder)
            };
            let ixs = [
                ComputeBudgetInstruction::set_compute_unit_limit(MATCHER_LAUNCH_CU_LIMIT),
                ComputeBudgetInstruction::set_compute_unit_price(1),
                ix,
            ];
            let message = if versioned {
                VersionedMessage::V0(v0::Message::try_compile(
                    &payer, &ixs, std::slice::from_ref(&static_table), hash,
                ).unwrap())
            } else {
                VersionedMessage::Legacy(Message::new_with_blockhash(&ixs, Some(&payer), &hash))
            };
            assert_eq!(message.header().num_required_signatures, 2);
            1 + 2 * 64 + message.serialize().len()
        };
        for (budget, versioned) in [(legacy, false), (v0, true)] {
            assert_eq!(wire_bytes(budget, versioned), PACKET_LIMIT, "{shape}");
            assert_eq!(wire_bytes(budget + 1, versioned), PACKET_LIMIT + 1, "{shape}");
        }
        rows.insert(shape, json!({"legacy":legacy,"v0_with_static_lookup_table":v0}));
    }
    review_evidence("metadata_packet_budgets", json!({"packet_limit":PACKET_LIMIT,
        "priority_price_instruction":true,"metadata_field_limit_bytes":242,"rows":rows}));
}
