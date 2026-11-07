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
fn door_open_sandwich_limit(front: u64, min_out: u64, max_room_price: u128) -> (bool, u64, u64, i128) {
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
    l.max_room_price = max_room_price;
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
fn review_room_price_limit_refuses_front_run_and_zero_accepts() {
    let mut f = Fixture::new(0);
    f.trade(None, true, 10_100_000_000);
    let price = f.r().price().unwrap();
    // Reduce before multiplying: these fixture constants fit u128 after division.
    let scaled = price.numerator * 1_000_000 / (price.denominator / 1_000_000_000_000);
    let limit = scaled * 102 / 100;
    let (ok, quote, _, _) = door_open_sandwich(0, 1);
    assert!(ok);
    for front in [5_000_000_000, 20_000_000_000, 60_000_000_000] {
        assert!(!door_open_sandwich_limit(front, quote * 98 / 100, limit).0);
        assert!(door_open_sandwich_limit(front, quote * 98 / 100, 0).0);
    }
    assert!(door_open_sandwich_limit(0, quote * 98 / 100, limit).0);
    // create_room enforces the same bound, including a launch without a first buy.
    let mut empty = Fixture::empty(0);
    let mut l = launch("Price bounded creation");
    l.max_room_price = 1;
    let ix = empty.create_ix(l.clone(), None);
    empty.fail_error(ix, true, Some("Slippage"));
    l.max_room_price = 0;
    empty.create(l, None);
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
    let ix = f.create_ix(second, None);
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
    let trace = 3 + meta.logs.iter().filter(|l| l.contains(" invoke [")).count();
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
            for i in 0..f.doors.len() {
                let held = f.balance(f.doors[i].user);
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
    f.claim(0, 0);
    let cfg = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    let protocol_before = f.r().protocol_accrued_sol;
    let wallet_before = lamports_of(&f, &f.user.pubkey());
    let mut volume = 0u128;
    let mut fee_rebate = 0u64;
    // Four trades/day, spaced at the maximum allowed six-hour interval.
    // Hold the floor position; alternate 1.25 SOL net buys and matching sells.
    let mut incremental = 0;
    for step in 0..8 {
        f.time(21_600);
        let before_volume = f.r().volume_gross;
        if step % 2 == 0 {
            let before = f.balance(f.doors[0].user);
            f.trade(Some(0), true, 1_262_500_001);
            incremental = f.balance(f.doors[0].user) - before;
        } else {
            f.trade(Some(0), false, incremental);
        }
        volume += f.r().volume_gross - before_volume;
        // Claim in the same transaction as the last trade of each day below;
        // the standalone fixture claim has the same state effect, +5,000 fee.
        if step % 4 == 3 {
            fee_rebate += f.d(0).accrued_sol;
            f.claim(0, 0);
        }
        if step >= 3 {
            assert!(f.r().live(&cfg, f.svm.get_sysvar::<Clock>().unix_timestamp).unwrap());
        }
        assert!(f.r().reserve >= 500_000_000);
    }
    let spent = wallet_before - lamports_of(&f, &f.user.pubkey());
    let protocol = f.r().protocol_accrued_sol - protocol_before;
    review_evidence("liveness_cost", json!({"days":2,"volume_lamports":volume.to_string(),
        "protocol_fees_lamports":protocol,"door_fees_reclaimed_lamports":fee_rebate,
        "wallet_cost_with_separate_claims_lamports":spent,"trade_transactions":8,
        "claim_transactions":2,"minimum_network_fee_per_day_bundled_lamports":20000,
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
