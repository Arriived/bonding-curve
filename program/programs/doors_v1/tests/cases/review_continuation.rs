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
fn door_open_sandwich(front: u64, min_out: u64) -> (bool, u64, u64, i128) {
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
