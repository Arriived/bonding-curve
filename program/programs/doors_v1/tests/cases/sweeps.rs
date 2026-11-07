// Included by svm.rs to share the real-SBF fixture. These are adversarial
// regressions against the compiled program, including the two confirmed findings.

#[test]
fn sweep_cross_room_swap_and_claim_substitution_rolls_back() {
    let mut f = Fixture::new(1000);
    f.open(launch("Local second face"));
    f.trade(Some(0), true, 1_010_000_000);
    let original = (f.rid, f.room, f.doors.clone());
    f.rid = 0x916a_041d_10e2_647b;
    f.room = p(&[b"room", &f.rid.to_le_bytes()]);
    f.doors.clear();
    f.create(launch("Foreign funded room"), None);
    f.trade(Some(0), true, 1_010_000_000);
    let foreign = f.core();
    let fd = f.doors[0].clone();
    (f.rid, f.room, f.doors) = original;
    let local = f.core();
    let ld = f.doors[0].clone();
    let mut attempts = 0;
    for (valid, replacement) in [
        (local.room, foreign.room),
        (local.reserve, foreign.reserve),
        (local.fees, foreign.fees),
        (local.room_mint, foreign.room_mint),
        (local.room_vault, foreign.room_vault),
        (local.retired, foreign.retired),
        (ld.door, fd.door),
        (ld.mint, fd.mint),
        (ld.vault, fd.vault),
        (ld.backing, fd.backing),
        (ld.user, fd.user),
        (
            p(&[b"swap_fees", local.room.as_ref()]),
            p(&[b"swap_fees", foreign.room.as_ref()]),
        ),
    ] {
        let mut instruction = f.swap_ix(0, 1, f.balance(ld.user) / 2);
        for meta in &mut instruction.accounts {
            if meta.pubkey == valid {
                meta.pubkey = replacement;
            }
        }
        f.fail(instruction, false);
        f.audit();
        attempts += 1;
    }
    for kind in 0..3 {
        for (valid, replacement) in [
            (local.room, foreign.room),
            (local.reserve, foreign.reserve),
            (local.fees, foreign.fees),
            (local.room_mint, foreign.room_mint),
            (local.room_vault, foreign.room_vault),
            (local.retired, foreign.retired),
            (f.r().fee_wsol, p(&[b"fee_wsol", foreign.room.as_ref()])),
            (ld.door, fd.door),
            (ld.mint, fd.mint),
            (ld.vault, fd.vault),
            (ld.backing, fd.backing),
        ] {
            let mut instruction = f.claim_ix(kind, 0, f.user.pubkey());
            let mut changed = false;
            for meta in &mut instruction.accounts {
                if meta.pubkey == valid {
                    meta.pubkey = replacement;
                    changed = true;
                }
            }
            if changed {
                f.fail(instruction, false);
                f.audit();
                attempts += 1;
            }
        }
    }
    assert_eq!(attempts, 37);
}

#[test]
fn sweep_signers_cannot_reassign_admin_or_fee_rights_and_open_cpi_rejects() {
    let mut f = Fixture::new(1000);
    let mut s = defaults(f.matcher.pubkey(), f.matcher.pubkey());
    s.founder_share_bps = 1000;
    f.fail(
        instr(
            a::UpdateConfig {
                admin: f.matcher.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings: s,
                new_admin: f.matcher.pubkey(),
            },
        ),
        true,
    );
    let d = f.doors[0].clone();
    f.fail_error(
        instr(
            a::SetRecipient {
                authority: f.matcher.pubkey(),
                core: f.core(),
                door: d.door,
                door_mint: d.mint,
                door_vault: d.vault,
                backing: d.backing,
            },
            ix::SetFeeRecipient {
                new_recipient: f.matcher.pubkey(),
            },
        ),
        true,
        Some("Authority"),
    );
    f.trade(Some(0), true, 1_010_000_000);
    for kind in 0..3 {
        let mut instruction = f.claim_ix(kind, 0, f.user.pubkey());
        for meta in &mut instruction.accounts {
            if meta.pubkey == f.user.pubkey() {
                meta.pubkey = f.matcher.pubkey();
            }
        }
        f.fail_error(instruction, true, Some("Authority"));
    }
    let proxy = Pubkey::new_from_array([29; 32]);
    let elf = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../target/deploy/launch_proxy.so");
    f.svm
        .add_program(proxy, &std::fs::read(elf).unwrap())
        .unwrap();
    let original = f.open_ix(launch("CPI second face"), None);
    let mut accounts = vec![AccountMeta::new_readonly(ID, false)];
    accounts.extend(original.accounts);
    f.fail_error(
        Instruction {
            program_id: proxy,
            accounts,
            data: original.data,
        },
        true,
        Some("LaunchCpi"),
    );
    assert_eq!(f.r().door_count, 1);
    f.audit();
}

#[test]
fn sweep_a_failed_last_instruction_rolls_back_prior_buys_and_swaps() {
    let mut f = Fixture::new(0);
    f.open(launch("Atomic second face"));
    let room_tokens = f.r().advance(1_000_000_000).unwrap() - f.r().sold;
    let tokens = doors_v1::math::door_advance(f.d(0).virtual_quote, 0, room_tokens).unwrap();
    let instructions = [
        ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
        f.trade_ix(Some(0), true, 1_010_000_000, tokens),
        f.swap_ix(0, 1, tokens / 2),
        f.trade_ix(Some(1), false, 1_000, u64::MAX),
    ];
    let tx = Transaction::new(
        &[&f.user],
        Message::new(&instructions, Some(&f.user.pubkey())),
        f.svm.latest_blockhash(),
    );
    let before: BTreeMap<_, _> = tx
        .message
        .account_keys
        .iter()
        .map(|key| (*key, f.svm.get_account(key)))
        .collect();
    let user_before = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
    let failure = f.svm.send_transaction(tx).unwrap_err();
    assert!(
        failure
            .meta
            .logs
            .iter()
            .any(|line| line.contains("Error Code: Slippage.")),
        "{failure:#?}"
    );
    for (key, account) in before {
        if key != f.user.pubkey() {
            assert_eq!(f.svm.get_account(&key), account);
        }
    }
    assert_eq!(
        user_before - f.svm.get_account(&f.user.pubkey()).unwrap().lamports,
        5000
    );
    assert_eq!(f.r().sold, 0);
    f.audit();
}

#[test]
fn sweep_repeated_completion_retirement_swap_and_exits_preserve_coverage() {
    let mut f = Fixture::new(1000);
    f.open(launch("Repeated cap face"));
    let room_ata = ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    );
    let reserve = p(&[b"reserve", f.room.as_ref()]);
    let fees = p(&[b"fees", f.room.as_ref()]);
    for _ in 0..32 {
        f.trade(None, true, u64::MAX / 100);
        assert_eq!(f.r().status, 1);
        f.trade(None, false, f.balance(room_ata) / 2);
        f.retire();
        f.trade(Some(0), true, u64::MAX / 100);
        assert_eq!(f.r().status, 1);
        let tokens = f.balance(f.doors[0].user);
        f.swap(0, 1, tokens);
        f.trade(Some(1), false, f.balance(f.doors[1].user));
        f.trade(None, false, f.balance(room_ata));
        assert_eq!(f.r().sold, f.unredeemed_room_tokens());
        assert_eq!(f.r().status, 0);
        for vault in [reserve, fees] {
            f.send(
                solana_system_interface::instruction::transfer(&f.user.pubkey(), &vault, 777),
                false,
                "sweep_surplus_donation",
            );
        }
        for kind in 0..3 {
            f.claim(kind, 0);
        }
        f.claim(0, 1);
        f.audit();
    }
    assert!(f.r().retired > 0);
}

#[test]
fn sweep_inverse_matches_independent_binary_search_for_20000_inputs() {
    let mut rng = 0x315c_a601_42e8_937bu64;
    let mut next = || {
        rng ^= rng << 13;
        rng ^= rng >> 7;
        rng ^= rng << 17;
        rng
    };
    for _ in 0..20000 {
        let vs = next().max(1);
        let vt = (next() % (u64::MAX - U - 1)) + U + 1;
        let budget = next();
        let reference = |q: u64| (vs as u128) * (vt as u128) / ((vt - q) as u128) - vs as u128;
        let (mut lo, mut hi) = (0, vt - 1);
        while lo < hi {
            let mid = lo + (hi - lo + 1) / 2;
            if reference(mid) <= budget as u128 {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        let actual = doors_v1::math::inverse(vs, vt, budget);
        if lo <= U {
            assert_eq!(actual.unwrap(), lo);
        } else {
            assert!(actual.is_err());
        }
        let gross = next().max(1);
        let bps = (next() % 10000) as u16;
        let available = next();
        let (net, fee) = doors_v1::math::buy_amounts(gross, bps, available).unwrap();
        assert!(net <= available);
        assert!(net as u128 + fee as u128 <= gross as u128);
        assert!(fee as u128 * 10000 >= net as u128 * bps as u128);
    }
}

#[test]
fn sweep_signed_launch_rejects_changed_curve_and_trade_fee_snapshot() {
    let mut f = Fixture::empty(0);
    let attacker = Keypair::new_from_array([33; 32]);
    f.svm.airdrop(&attacker.pubkey(), 100_000_000).unwrap();
    let original = defaults(f.matcher.pubkey(), attacker.pubkey());
    f.send(
        instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings: original.clone(),
                new_admin: attacker.pubkey(),
            },
        ),
        false,
        "sweep_admin_setup",
    );
    let mut l = launch("Snapshot race witness");
    l.first_buy_lamports = 1_010_000_000;
    l.min_tokens_out =
        doors_v1::math::inverse(original.v_sol_lamports, original.v_tok, 1_000_000_000).unwrap();
    let min_tokens = l.min_tokens_out;
    let tx = Transaction::new(
        &[&f.user, &f.matcher],
        Message::new(
            &[
                ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                f.create_ix(l, None),
            ],
            Some(&f.user.pubkey()),
        ),
        f.svm.latest_blockhash(),
    );
    let signed_message = tx.message_data();
    let mut changed = original;
    changed.fee_bps = 9999;
    changed.door_share_bps = 0;
    changed.v_sol_lamports /= 2;
    audit_send_as(
        &mut f,
        &attacker,
        instr(
            a::UpdateConfig {
                admin: attacker.pubkey(),
                config: p(&[b"config"]),
            },
            ix::UpdateConfig {
                settings: changed,
                new_admin: attacker.pubkey(),
            },
        ),
    );
    tx.verify().unwrap();
    assert_eq!(tx.message_data(), signed_message);
    let before: BTreeMap<_, _> = tx
        .message
        .account_keys
        .iter()
        .map(|key| (*key, f.svm.get_account(key)))
        .collect();
    let failure = f.svm.send_transaction(tx).unwrap_err();
    assert!(
        failure
            .meta
            .logs
            .iter()
            .any(|line| line.contains("Error Code: LaunchTerms.")),
        "{failure:#?}"
    );
    for (key, account) in before {
        if key != f.user.pubkey() {
            assert_eq!(f.svm.get_account(&key), account);
        }
    }
    assert!(f.svm.get_account(&f.room).is_none());
    let output = json!({"finding": "launch Config snapshot race", "fixed": true,
        "signed_message_unchanged": true, "signed_min_tokens": min_tokens,
        "rejected_with": "LaunchTerms", "all_other_accounts_unchanged": true});
    std::fs::write(
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification/sweep_config_race.json"),
        serde_json::to_string_pretty(&output).unwrap() + "\n",
    )
    .unwrap();
}

// Valid legacy state produced by 100 fee-paying room-route round trips in
// the pre-fix SBF witness (436c002). Seed it explicitly because new buys now
// settle pending fees and cannot reproduce that old accumulation schedule.
fn sweep_legacy_backlog() -> Fixture {
    let mut f = Fixture::new(0);
    let fees = f.core().fees;
    f.send(
        solana_system_interface::instruction::transfer(&f.user.pubkey(), &fees, 20_000_000_000),
        false,
        "legacy_fee_funding",
    );
    let mut r = f.r();
    r.pending_reserve_sol = 12_000_000_000;
    r.protocol_accrued_sol = 8_000_000_000;
    let mut account = f.svm.get_account(&f.room).unwrap();
    r.try_serialize(&mut &mut account.data[..]).unwrap();
    f.svm.set_account(f.room, account).unwrap();
    f.audit();
    f
}

fn sweep_post_retirement_tokens(r: &Room, net: u64) -> u64 {
    let q = r
        .advance(
            r.pending_reserve_sol
                .min(r.graduation_trigger_lamports - r.reserve),
        )
        .unwrap();
    doors_v1::math::inverse(r.v_sol_lamports, r.v_tok, r.curve(q).unwrap() + net).unwrap() - q
}

#[test]
fn sweep_atomic_temporary_holder_cannot_capture_legacy_pending_on_either_route() {
    let mut evidence = Vec::new();
    for route in [None, Some(0)] {
        let mut f = sweep_legacy_backlog();
        f.user = Keypair::new_from_array([33; 32]);
        f.svm.airdrop(&f.user.pubkey(), 100_000_000_000).unwrap();
        let mint = route.map_or(f.r().room_mint, |i| f.doors[i].mint);
        let attacker_ata = ata(f.user.pubkey(), mint, spl_token_2022_interface::ID);
        f.make_ata(mint, spl_token_2022_interface::ID);
        f.doors[0].user = ata(
            f.user.pubkey(),
            f.doors[0].mint,
            spl_token_2022_interface::ID,
        );
        let tokens = sweep_post_retirement_tokens(&f.r(), 60_000_000_000);
        let core = f.core();
        let retired_output = core.retired;
        let retire = instr(
            a::Retire {
                core,
                retired_output,
                token_program: spl_token_2022_interface::ID,
            },
            ix::RetirePending {},
        );
        let tx = Transaction::new(
            &[&f.user],
            Message::new(
                &[
                    ComputeBudgetInstruction::set_compute_unit_limit(1_400_000),
                    f.trade_ix(route, true, 60_600_000_000, tokens),
                    retire,
                    f.trade_ix(route, false, tokens, 0),
                ],
                Some(&f.user.pubkey()),
            ),
            f.svm.latest_blockhash(),
        );
        let before = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
        f.svm.send_transaction(tx).unwrap();
        let profit = f.svm.get_account(&f.user.pubkey()).unwrap().lamports as i128 - before as i128;
        assert!(profit < 0, "temporary holder profit {profit}");
        assert_eq!(f.balance(attacker_ata), 0);
        assert_eq!(f.r().sold, f.unredeemed_room_tokens());
        assert!(f.r().retired > 0);
        // Legacy protocol fees remain fully accrued to their beneficiary.
        assert!(f.r().protocol_accrued_sol >= 8_000_000_000);
        f.audit();
        evidence.push(json!({"route": if route.is_some() {"door"} else {"room"},
            "legacy_pending_before": 12_000_000_000u64, "fixed": true,
            "single_transaction": true, "attacker_tokens_after": 0,
            "attacker_profit_after_network_fee": profit,
            "all_accounting_invariants_hold": true}));
    }
    std::fs::write(
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../verification/sweep_retirement_mev.json"),
        serde_json::to_string_pretty(&evidence).unwrap() + "\n",
    )
    .unwrap();
}

#[test]
fn sweep_open_first_buy_settles_legacy_pending_and_slippage_rolls_it_back() {
    let mut f = sweep_legacy_backlog();
    let tokens = sweep_post_retirement_tokens(&f.r(), 1_000_000_000);
    let mut l = launch("Retirement first buy");
    l.first_buy_lamports = 1_010_000_000;
    l.min_tokens_out = tokens + 1;
    f.fail_error(f.open_ix(l.clone(), None), true, Some("Slippage"));
    assert_eq!(f.r().pending_reserve_sol, 12_000_000_000);
    assert_eq!(f.r().retired, 0);
    l.min_tokens_out = tokens;
    f.open(l);
    assert_eq!(f.r().pending_reserve_sol, 0);
    assert_eq!(f.balance(f.doors[1].user), tokens);
    assert_eq!(f.r().reserve, 13_000_000_000);
    f.audit();
}

#[test]
fn sweep_room_and_door_buy_slippage_roll_back_automatic_retirement() {
    for route in [None, Some(0)] {
        let mut f = sweep_legacy_backlog();
        let tokens = sweep_post_retirement_tokens(&f.r(), 1_000_000_000);
        f.fail_error(
            f.trade_ix(route, true, 1_010_000_000, tokens + 1),
            false,
            Some("Slippage"),
        );
        assert_eq!(f.r().pending_reserve_sol, 12_000_000_000);
        assert_eq!(f.r().retired, 0);
        f.checked(
            f.trade_ix(route, true, 1_010_000_000, tokens),
            false,
            "buy_with_retirement",
        );
        f.audit();
        assert_eq!(f.r().retired + tokens, f.r().sold);
    }
}

#[test]
fn sweep_new_trades_cannot_build_the_legacy_delayed_fee_backlog() {
    let mut f = Fixture::new(0);
    let user_ata = ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    );
    for _ in 0..100 {
        f.trade(None, true, 10_100_000_000);
        f.trade(None, false, f.balance(user_ata));
        assert!(f.r().pending_reserve_sol < 200_000_000);
    }
    assert!(f.r().retired > 0);
    f.audit();
}

#[test]
fn sweep_every_mutable_room_economic_term_is_bound_to_signed_launches() {
    for kind in 0..7 {
        let mut f = Fixture::empty(0);
        let signed = f.create_ix(launch("All launch terms"), None);
        let mut s = defaults(f.matcher.pubkey(), f.user.pubkey());
        match kind {
            0 => s.v_sol_lamports /= 2,
            1 => s.v_tok += 1_000_000,
            2 => s.r_star_lamports -= 1,
            3 => s.graduation_trigger_lamports += 1,
            4 => s.fee_bps += 1,
            5 => s.door_share_bps -= 1,
            _ => s.founder_share_bps += 1,
        }
        audit_settings(&mut f, s);
        f.fail_error(signed, true, Some("LaunchTerms"));
        // A refreshed instruction binds and copies the new terms successfully.
        f.create(launch("All launch terms"), None);
    }
}
