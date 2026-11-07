// Additional pre-devnet sweep. All economic amounts come from real SBF
// execution. No RPC, deployment or production keys are used by these tests.
fn adversarial_evidence(name: &str, data: Value) {
    println!("ADVERSARIAL_REVIEW {data}");
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(format!("../../verification/adversarial_{name}.json"));
    std::fs::write(path, serde_json::to_string_pretty(&data).unwrap() + "\n").unwrap();
}

#[test]
fn adversarial_revived_former_holder_still_accepts_routed_flow() {
    let mut f = Fixture::empty(0);
    let wallet_start = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    let mut first = launch("Revival Frog");
    first.symbol = "OLD".into();
    let name = Fixture::name_key(&first);
    f.create(first, None);
    let setup_cost = wallet_start - f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    f.trade(Some(0), true, 1_010_000_000);
    f.claim(0, 0);
    let old = (f.rid, f.room, f.doors.clone());
    let c = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    f.time(90_000);
    assert!(!f
        .r()
        .live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());

    let mut other = Keypair::new_from_array([63; 32]);
    f.svm.airdrop(&other.pubkey(), 10_000_000_000).unwrap();
    paired_actor(&mut f, &mut other);
    f.rid += 1;
    f.room = p(&[b"room", &f.rid.to_le_bytes()]);
    f.doors.clear();
    let mut successor = launch("Revival Frog");
    successor.symbol = "NEW".into();
    f.create(successor, None);
    let current = f.room;
    assert_eq!(f.name_holder(&name), Some(current));
    let current_room = f.r();
    assert!(current_room
        .live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    paired_actor(&mut f, &mut other);
    (f.rid, f.room, f.doors) = old;

    let held = f.balance(f.doors[0].user);
    let before_wash = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    f.trade(Some(0), true, 2_525_000_100);
    let acquired = f.balance(f.doors[0].user) - held;
    f.trade(Some(0), false, acquired);
    let own_fees = f.d(0).accrued_sol;
    f.claim(0, 0);
    let revival_cost = before_wash - f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    assert!(f
        .r()
        .live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    assert!(f.r().reserve > current_room.reserve);
    assert_eq!(f.name_holder(&name), Some(current));

    // The service reproduction selects this revived room for a third symbol.
    // Show that the program accepts that signed route while the successor lives.
    paired_actor(&mut f, &mut other);
    let mut routed = launch("Revival Frog");
    routed.symbol = "THIRD".into();
    routed.first_buy_lamports = 1_010_000_000;
    routed.min_tokens_out = 1;
    f.open(routed);
    paired_actor(&mut f, &mut other);
    let before_exit = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    f.trade(Some(0), false, held);
    f.claim(0, 0);
    let exit_received = f.svm.get_account(&f.user.pubkey()).unwrap().lamports - before_exit;
    let final_wallet = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    assert_eq!(f.name_holder(&name), Some(current));
    adversarial_evidence(
        "revival",
        json!({
            "case":"revival_after_name_takeover", "owner_decision":true,
            "setup_cost_lamports":setup_cost, "recoverable_initial_reserve_lamports":1_000_000_000u64,
            "initial_gross_buy_lamports":1_010_000_000u64,
            "revival_operating_cost_lamports":revival_cost, "own_wash_fees_claimed_lamports":own_fees,
            "victim_first_buy_lamports":1_010_000_000u64, "exit_received_after_fees_lamports":exit_received,
            "attacker_wallet_net_lamports":i128::from(final_wallet)-i128::from(wallet_start),
            "successor_remains_live":current_room.live(&c, f.svm.get_sysvar::<Clock>().unix_timestamp).unwrap(),
            "name_lock_still_points_to_successor":true
        }),
    );
    f.audit();
}

#[test]
fn adversarial_swap_donations_pause_and_claims_preserve_exit() {
    let mut f = Fixture::new(0);
    f.open(launch("Donation destination"));
    f.trade(Some(0), true, 2_020_000_000);
    f.trade(None, true, 1_010_000_000);
    f.swap(0, 1, f.balance(f.doors[0].user) / 2);
    let vault = p(&[b"swap_fees", f.room.as_ref()]);
    let room_ata = ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    );
    let room_before = f.r();
    let credit = room_before.swap_fees_unclaimed;
    let before = f.swap_fee_balance();
    f.send(
        spl_token_2022_interface::instruction::transfer_checked(
            &spl_token_2022_interface::ID,
            &room_ata,
            &f.r().room_mint,
            &vault,
            &f.user.pubkey(),
            &[],
            777,
            6,
        )
        .unwrap(),
        false,
        "donate_swap_room_tokens",
    );
    for address in [
        vault,
        f.core().reserve,
        f.core().fees,
        f.r().fee_wsol,
        f.doors[0].backing,
        p(&[b"grad_payer", f.room.as_ref()]),
    ] {
        f.send(
            solana_system_interface::instruction::transfer(&f.user.pubkey(), &address, 777),
            false,
            "donate_native_lamports",
        );
    }
    f.send(
        spl_token_interface::instruction::sync_native(&spl_token_interface::ID, &f.r().fee_wsol)
            .unwrap(),
        false,
        "sync_donated_native_tokens",
    );
    assert_eq!(f.r().reserve, room_before.reserve);
    assert_eq!(f.r().sold, room_before.sold);
    assert_eq!(f.r().swap_fees_unclaimed, credit);
    assert_eq!(f.swap_fee_balance(), before + 777);
    let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
    settings.paused = true;
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
        "pause",
    );
    f.swap(1, 0, f.balance(f.doors[1].user) / 2);
    f.claim_swap(Some(0));
    f.claim_swap(Some(1));
    f.claim_swap(None);
    f.claim_swap(None);
    assert_eq!(f.r().swap_fees_unclaimed, 0);
    assert_eq!(f.swap_fee_balance(), 777);
    for i in 0..2 {
        f.trade(Some(i), false, f.balance(f.doors[i].user));
        f.claim(0, i);
    }
    f.trade(None, false, f.balance(room_ata));
    f.claim(2, 0);
    f.audit();
}

#[test]
fn adversarial_swap_claim_account_substitution_and_optional_aliases() {
    let mut f = Fixture::new(0);
    f.open(launch("Claim substitution destination"));
    f.trade(Some(0), true, 2_020_000_000);
    f.swap(0, 1, f.balance(f.doors[0].user) / 2);
    let mut count = 0;
    for selected in [None, Some(0), Some(1)] {
        let original = f.claim_swap_ix(selected);
        for index in 1..original.accounts.len() {
            // Optional None accounts are the program-id sentinel. Other
            // non-signer accounts may never be replaced by an unrelated one.
            if original.accounts[index].pubkey == ID {
                continue;
            }
            let mut bad = original.clone();
            bad.accounts[index].pubkey = spl_token_interface::ID;
            f.fail(bad, false);
            count += 1;
        }
    }
    let original = f.claim_swap_ix(Some(1));
    for (from, to) in [
        (f.doors[1].mint, f.doors[1].vault),
        (f.doors[1].vault, f.doors[1].backing),
        (f.doors[1].backing, f.doors[1].vault),
    ] {
        let mut bad = original.clone();
        for m in &mut bad.accounts {
            if m.pubkey == from {
                m.pubkey = to;
            }
        }
        f.fail(bad, false);
        count += 1;
    }
    f.claim_swap(Some(0));
    f.claim_swap(Some(1));
    f.claim_swap(None);
    assert_eq!(f.r().swap_fees_unclaimed, 0);
    adversarial_evidence(
        "claim_substitutions",
        json!({"case":"swap_claim_substitution",
        "rejected_attempts":count,"attacker_fee_per_failed_transaction_lamports":5000,
        "direct_payoff_lamports":0}),
    );
    f.audit();
}

#[test]
fn adversarial_self_owned_swap_loops_cannot_extract_room_value() {
    let mut results = Vec::new();
    for initial in [0, 10, 50] {
        let mut f = Fixture::new(0);
        // The attacker owns doors, not the protocol fee authority.
        let settings = defaults(f.matcher.pubkey(), f.matcher.pubkey());
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
            "separate_protocol",
        );
        if initial > 0 {
            f.trade(Some(0), true, initial * 1_010_000_000);
        }
        f.open(launch("Loop source"));
        f.open(launch("Loop destination"));
        let start = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
        f.trade(Some(1), true, 1_010_000_000);
        let room_before = f.r();
        for _ in 0..8 {
            f.swap(1, 2, f.balance(f.doors[1].user));
            f.swap(2, 1, f.balance(f.doors[2].user));
        }
        assert_eq!(f.r().sold, room_before.sold);
        assert_eq!(f.r().reserve, room_before.reserve);
        let charged = f.r().swap_fees_unclaimed;
        let protocol = f.r().protocol_accrued_room;
        f.claim_swap(Some(1));
        f.claim_swap(Some(2));
        assert_eq!(f.r().swap_fees_unclaimed, protocol);
        let room_ata = ata(
            f.user.pubkey(),
            f.r().room_mint,
            spl_token_2022_interface::ID,
        );
        f.trade(Some(1), false, f.balance(f.doors[1].user));
        f.trade(None, false, f.balance(room_ata));
        f.claim(0, 1);
        f.claim(0, 2);
        let end = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
        assert!(end < start);
        results.push(json!({"initial_room_sol":initial,"round_trips":8,
            "net_cost_lamports":start-end,"swap_fees_room_base":charged,
            "self_claimed_swap_fees_room_base":charged-protocol,
            "protocol_swap_fees_room_base":protocol,"direct_profit_lamports":0}));
        f.audit();
    }
    adversarial_evidence("swap_loops", json!(results));
}

#[test]
fn adversarial_normal_admin_can_select_the_stress_cap() {
    let mut f = Fixture::new(0);
    let old_cap = f.r().graduation_trigger_lamports;
    let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
    settings.graduation_trigger_lamports = 120_000_000_000;
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
        "normal_admin_stress_cap",
    );
    let c = Config::try_deserialize(&mut &f.svm.get_account(&f.cfg).unwrap().data[..]).unwrap();
    // Existing rooms keep the cap they were created with.
    assert_eq!(f.r().graduation_trigger_lamports, old_cap);
    // Finding, recorded as current behaviour (owner decision pending, SECURITY_REVIEW.md): a normal admin
    // update selects the 120 SOL stress cap for every room created afterwards. If the owner rules that
    // production builds must refuse it, this assertion flips to `old_cap` together with the program change.
    assert_eq!(c.graduation_trigger_lamports, 120_000_000_000);
    adversarial_evidence(
        "stress_cap",
        json!({"case": "normal admin update selects the stress cap", "owner_decision": true,
               "existing_room_cap_lamports": old_cap, "new_rooms_cap_lamports": c.graduation_trigger_lamports}),
    );
}
