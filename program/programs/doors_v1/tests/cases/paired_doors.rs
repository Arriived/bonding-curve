fn paired_actor(f: &mut Fixture, wallet: &mut Keypair) {
    std::mem::swap(&mut f.user, wallet);
    for door in &mut f.doors {
        door.user = ata(f.user.pubkey(), door.mint, spl_token_2022_interface::ID);
    }
}

fn paired_spot(room: &Room) -> f64 {
    let price = room.price().unwrap();
    price.numerator as f64 / price.denominator as f64
}

fn paired_door_spot(door: &Door) -> f64 {
    let base = doors_v1::math::DOOR_VIRTUAL_BASE as f64;
    door.virtual_quote as f64 * base / (base - door.sold as f64).powi(2)
}

fn paired_snapshot(f: &Fixture, start_price: f64, step: &str) -> Value {
    let room = f.r();
    let spot = paired_spot(&room);
    json!({
        "step": step,
        "room_sold_base": room.sold,
        "room_reserve_lamports": room.reserve,
        "room_price_multiple": spot / start_price,
        "doors": (0..f.doors.len()).map(|i| {
            let door = f.d(i);
            json!({
                "index": i,
                "room_reserve_base": door.backing,
                "door_sold_base": door.sold,
                "fdv_sol": paired_door_spot(&door) * spot * U as f64 / 1e9
            })
        }).collect::<Vec<_>>()
    })
}

fn paired_dump(f: &mut Fixture) {
    let price = paired_spot(&f.r());
    let room = f.r();
    let door = f.d(0);
    let integral = doors_v1::math::door_integral(door.virtual_quote, door.sold).unwrap();
    let needed = ((room.v_tok - room.sold) as f64 * (2.0_f64.sqrt() - 1.0)).round() as u64;
    let mut lo = 0;
    let mut hi = f.balance(f.doors[0].user);
    assert!(
        integral >= needed,
        "the unrelated seller must cover the dump"
    );
    while hi - lo > 1 {
        let mid = lo + (hi - lo) / 2;
        let payout =
            integral - doors_v1::math::door_integral(door.virtual_quote, door.sold - mid).unwrap();
        if payout >= needed {
            hi = mid;
        } else {
            lo = mid;
        }
    }
    f.trade(Some(0), false, hi);
    assert!((paired_spot(&f.r()) / price - 0.5).abs() < 1e-6);
}

fn paired_scenario(initial_sol: u64, rotate: bool, dump: bool) -> Value {
    use doors_v1::math::ratio;
    let mut f = Fixture::new(0);
    if initial_sol != 0 {
        f.trade(Some(0), true, initial_sol * 1_010_000_000);
    }
    let initial = f.r();
    assert_eq!(initial.reserve, initial_sol * 1_000_000_000);
    let start_price = paired_spot(&initial);

    f.open(launch("Rotation destination"));
    let destination = 1;
    let source = 2;
    let mut a = Keypair::new();
    f.svm.airdrop(&a.pubkey(), 10_000_000_000).unwrap();
    paired_actor(&mut f, &mut a);
    let mut first = launch("Follower source door");
    first.first_buy_lamports = 2_000_000_000;
    f.open(first);
    let a_tokens = f.balance(f.doors[source].user);
    let quote = f.d(source).virtual_quote as f64 / doors_v1::math::DOOR_VIRTUAL_BASE as f64;
    let launch_fdv = quote * start_price * U as f64 / 1e9;
    let mut steps = vec![paired_snapshot(&f, start_price, "after_a_buys")];
    let room_input = f.r().reserve - initial.reserve;
    let room_only_out = initial.advance(room_input).unwrap() - initial.sold;
    let ideal_room_out = room_input as f64 / start_price;
    let paired_buy_slippage = 1.0 - a_tokens as f64 / (ideal_room_out / quote);
    let single_buy_slippage = 1.0 - room_only_out as f64 / ideal_room_out;
    paired_actor(&mut f, &mut a);

    let mut followers = Vec::new();
    for _ in 0..20 {
        let mut follower = Keypair::new();
        f.svm.airdrop(&follower.pubkey(), 2_000_000_000).unwrap();
        paired_actor(&mut f, &mut follower);
        for index in [source, destination] {
            f.make_ata(f.doors[index].mint, spl_token_2022_interface::ID);
        }
        f.trade(Some(source), true, 1_000_000_000);
        paired_actor(&mut f, &mut follower);
        followers.push(follower);
    }
    steps.push(paired_snapshot(&f, start_price, "after_followers_buy"));
    if dump {
        paired_dump(&mut f);
        steps.push(paired_snapshot(
            &f,
            start_price,
            "after_unrelated_room_dump",
        ));
    }

    paired_actor(&mut f, &mut a);
    let room_before = f.r();
    let notional_room_tokens = (a_tokens as f64 * paired_door_spot(&f.d(source))) as u64;
    let ideal_sell_sol = notional_room_tokens as f64
        * paired_spot(&room_before)
        * (1.0 - room_before.fee_bps as f64 / 10000.0);
    let single_gross = room_before.curve(room_before.sold).unwrap()
        - room_before
            .curve(room_before.sold - notional_room_tokens)
            .unwrap();
    let single_net = single_gross - ratio(single_gross, room_before.fee_bps, true).unwrap();
    f.trade(Some(source), false, a_tokens);
    let gross = room_before.reserve - f.r().reserve;
    let a_out = gross - ratio(gross, room_before.fee_bps, true).unwrap();
    paired_actor(&mut f, &mut a);
    steps.push(paired_snapshot(&f, start_price, "after_a_exits"));

    let mut swap_slippage = None;
    for mut follower in followers {
        paired_actor(&mut f, &mut follower);
        let tokens = f.balance(f.doors[source].user);
        if rotate {
            if swap_slippage.is_none() {
                let from = f.d(source);
                let to = f.d(destination);
                let spot_room = (tokens as f64 * paired_door_spot(&from)) as u64;
                let single_quote = spot_room - ratio(spot_room, 100, true).unwrap();
                let ideal_out = single_quote as f64 / paired_door_spot(&to);
                let single_out =
                    doors_v1::math::door_advance(to.virtual_quote, to.sold, single_quote).unwrap()
                        - to.sold;
                let balance = f.balance(f.doors[destination].user);
                f.swap(source, destination, tokens);
                let actual = f.balance(f.doors[destination].user) - balance;
                swap_slippage = Some(json!({
                    "paired_bps": 10000.0 * (1.0 - actual as f64 / ideal_out),
                    "single_door_bps": 10000.0 * (1.0 - single_out as f64 / ideal_out),
                    "extra_bps": 10000.0 * (single_out as f64 - actual as f64) / ideal_out,
                }));
            } else {
                f.swap(source, destination, tokens);
            }
        } else {
            f.trade(Some(source), false, tokens);
        }
        paired_actor(&mut f, &mut follower);
    }
    steps.push(paired_snapshot(
        &f,
        start_price,
        if rotate {
            "after_followers_rotate"
        } else {
            "after_followers_cash_out"
        },
    ));
    json!({
        "initial_room_sol": initial_sol,
        "dump": dump,
        "followers_rotate": rotate,
        "a_payout_lamports": a_out,
        "source_door_launch_fdv_sol": launch_fdv,
        "first_rotation_swap_slippage": swap_slippage,
        "buy_slippage": {
            "paired_bps": 10000.0 * paired_buy_slippage,
            "single_room_bps": 10000.0 * single_buy_slippage,
            "extra_bps": 10000.0 * (paired_buy_slippage - single_buy_slippage),
        },
        "sell_slippage": {
            "paired_bps": 10000.0 * (1.0 - a_out as f64 / ideal_sell_sol),
            "single_room_bps": 10000.0 * (1.0 - single_net as f64 / ideal_sell_sol),
            "extra_bps": 10000.0 * (single_net as f64 - a_out as f64) / ideal_sell_sol,
        },
        "steps": steps,
    })
}

#[test]
fn paired_doors_late_buyer_and_room_dump() {
    let mut evidence = Vec::new();
    for initial in [0, 10, 50] {
        for rotate in [false, true] {
            evidence.push(paired_scenario(initial, rotate, false));
            if initial != 0 {
                evidence.push(paired_scenario(initial, rotate, true));
            }
        }
    }
    for row in &evidence {
        println!("PAIRED_DOORS_SCENARIO {row}");
    }
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification/paired_doors.json");
    std::fs::write(
        path,
        serde_json::to_string_pretty(&evidence).unwrap() + "\n",
    )
    .unwrap();
}

#[test]
fn paired_door_trade_limits_and_launch_rent() {
    let mut trade_rows = Vec::new();
    for prefunded in [false, true] {
        for priority in [false, true] {
            for shape in [
                "buy_room",
                "sell_room",
                "buy_door",
                "sell_door",
                "swap_doors",
                "swap_doors_existing",
                "claim_door_swap_fees",
                "claim_protocol_swap_fees",
            ] {
                let mut f = Fixture::new(0);
                f.open(launch("Trade limit second door"));
                f.trade(None, true, 1_010_000_000);
                f.trade(Some(0), true, 1_010_000_000);
                if matches!(
                    shape,
                    "swap_doors_existing" | "claim_door_swap_fees" | "claim_protocol_swap_fees"
                ) {
                    f.swap(0, 1, f.balance(f.doors[0].user) / 4);
                }
                let room_ata = ata(
                    f.user.pubkey(),
                    f.r().room_mint,
                    spl_token_2022_interface::ID,
                );
                let ix = match shape {
                    "buy_room" => f.trade_ix(None, true, 1_010_000_000, 1),
                    "sell_room" => f.trade_ix(None, false, f.balance(room_ata) / 2, 1),
                    "buy_door" => f.trade_ix(Some(1), true, 1_010_000_000, 1),
                    "sell_door" => f.trade_ix(Some(0), false, f.balance(f.doors[0].user) / 2, 1),
                    "claim_door_swap_fees" => f.claim_swap_ix(Some(1)),
                    "claim_protocol_swap_fees" => f.claim_swap_ix(None),
                    _ => f.swap_ix(0, 1, f.balance(f.doors[0].user) / 2),
                };
                if prefunded {
                    let rent = f.svm.minimum_balance_for_rent_exemption(0);
                    for account in &ix.accounts {
                        if account.is_writable && !account.is_signer {
                            f.svm.airdrop(&account.pubkey, rent).unwrap();
                        }
                    }
                }
                f.svm.expire_blockhash();
                let mut instructions =
                    vec![ComputeBudgetInstruction::set_compute_unit_limit(400_000)];
                if priority {
                    instructions.push(ComputeBudgetInstruction::set_compute_unit_price(1));
                }
                instructions.push(ix);
                let tx = Transaction::new(
                    &[&f.user],
                    Message::new(&instructions, Some(&f.user.pubkey())),
                    f.svm.latest_blockhash(),
                );
                let result = f.svm.send_transaction(tx).unwrap_or_else(|e| {
                    panic!("paired doors limit {shape} prefunded={prefunded} priority={priority}: {e:#?}")
                });
                let count = result
                    .logs
                    .iter()
                    .filter(|log| log.contains(" invoke ["))
                    .count();
                let prefix = format!("Program {ID} consumed ");
                let program_cu = result
                    .logs
                    .iter()
                    .find_map(|line| {
                        line.strip_prefix(&prefix)?
                            .split_whitespace()
                            .next()?
                            .parse::<u64>()
                            .ok()
                    })
                    .expect("program CU log");
                let row = json!({"shape": shape, "prefunded": prefunded, "priority_fee": priority,
                                 "trace_entries": count, "transaction_cu": result.compute_units_consumed,
                                 "program_cu": program_cu});
                println!("PAIRED_DOORS_TRADE_LIMIT {row}");
                assert!(count <= 52, "{row}");
                assert!(result.compute_units_consumed <= 400_000, "{row}");
                f.audit();
                trade_rows.push(row);
            }
        }
    }

    let mut f = Fixture::empty(0);
    let room_ix = f.create_ix(launch("Rent measurement room"), None);
    let fresh_accounts = |fixture: &Fixture, ix: &Instruction| -> Vec<Pubkey> {
        ix.accounts
            .iter()
            .filter(|account| {
                account.is_writable && fixture.svm.get_account(&account.pubkey).is_none()
            })
            .map(|account| account.pubkey)
            .collect::<std::collections::BTreeSet<_>>()
            .into_iter()
            .collect()
    };
    let addresses = fresh_accounts(&f, &room_ix);
    f.send(room_ix, true, "paired_rent_create_room");
    let room_rent: u64 = addresses
        .iter()
        .filter_map(|key| f.svm.get_account(key))
        .map(|account| account.lamports)
        .sum();
    let open_ix = f.open_ix(launch("Rent measurement door"), None);
    let addresses = fresh_accounts(&f, &open_ix);
    f.send(open_ix, true, "paired_rent_open_door");
    let door_rent: u64 = addresses
        .iter()
        .filter_map(|key| f.svm.get_account(key))
        .map(|account| account.lamports)
        .sum();
    let mut swap_fixture = Fixture::new(0);
    swap_fixture.open(launch("First swap rent destination"));
    swap_fixture.trade(Some(0), true, 1_010_000_000);
    swap_fixture.swap(0, 1, swap_fixture.balance(swap_fixture.doors[0].user) / 2);
    let first_swap_vault_rent = swap_fixture
        .svm
        .get_account(&p(&[b"swap_fees", swap_fixture.room.as_ref()]))
        .unwrap()
        .lamports;
    let rent = json!({"room_with_door_0_lamports": room_rent,
                      "additional_door_lamports": door_rent,
                      "first_swap_vault_lamports": first_swap_vault_rent,
                      "first_buy": false, "uri": "https://example.invalid/m.json"});
    println!("PAIRED_DOORS_RENT {rent}");
    let evidence = json!({"trades": trade_rows, "rent": rent});
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../verification/paired_limits.json");
    std::fs::write(
        path,
        serde_json::to_string_pretty(&evidence).unwrap() + "\n",
    )
    .unwrap();
}

#[test]
fn paired_swap_vault_is_lazy_prefundable_and_atomic() {
    for prefunded in [false, true] {
        let mut f = Fixture::new(0);
        f.open(launch("Lazy swap destination"));
        f.trade(Some(0), true, 1_010_000_000);
        let vault = p(&[b"swap_fees", f.room.as_ref()]);
        assert!(f.svm.get_account(&vault).is_none());
        let rent = f.svm.minimum_balance_for_rent_exemption(165);
        if prefunded {
            f.svm.airdrop(&vault, rent / 2).unwrap();
        }
        let held = f.balance(f.doors[0].user);
        let mut invalid = f.swap_ix(0, 1, held / 3);
        let destination = f.doors[1].user;
        for account in &mut invalid.accounts {
            if account.pubkey == destination {
                account.pubkey = f.doors[0].user;
            }
        }
        let before = f.svm.get_account(&vault);
        f.fail_error(invalid, false, Some("Account"));
        assert_eq!(f.svm.get_account(&vault), before);
        let before_user = f.svm.get_account(&f.user.pubkey()).unwrap().lamports;
        f.swap(0, 1, held / 3);
        let created = f.svm.get_account(&vault).unwrap();
        assert_eq!(created.owner, spl_token_2022_interface::ID);
        assert_eq!(created.lamports, rent);
        // The destination backing is also created on its first receiving swap.
        let paid_rent = 2 * rent - before.as_ref().map_or(0, |account| account.lamports);
        assert_eq!(
            before_user - f.svm.get_account(&f.user.pubkey()).unwrap().lamports,
            paid_rent + 5_000
        );
        f.swap(0, 1, held / 3);
        assert_eq!(f.svm.get_account(&vault).unwrap().lamports, rent);
        f.audit();
    }
}

#[test]
fn paired_swap_claims_require_entitlement_and_pay_every_fee() {
    let mut f = Fixture::new(0);
    f.open(launch("First fee recipient"));
    f.open(launch("Second fee recipient"));
    f.trade(Some(0), true, 5_050_000_000);
    let mut charged = 0;
    for (from, to) in [(0, 1), (0, 2), (1, 2)] {
        let tokens = f.balance(f.doors[from].user) / 2;
        let door = f.d(from);
        let gross = doors_v1::math::door_integral(door.virtual_quote, door.sold).unwrap()
            - doors_v1::math::door_integral(door.virtual_quote, door.sold - tokens).unwrap();
        let expected = doors_v1::math::ratio(gross, doors_v1::math::SWAP_FEE_BPS, true).unwrap();
        let before = f.swap_fee_balance();
        f.swap(from, to, tokens);
        assert_eq!(f.swap_fee_balance() - before, expected);
        charged += expected;
    }
    assert!(f.d(1).accrued_room > 0 && f.d(2).accrued_room > 0);
    assert_eq!(charged, f.r().swap_fees_unclaimed);
    let entitled = std::mem::replace(&mut f.user, Keypair::new());
    f.svm.airdrop(&f.user.pubkey(), 10_000_000).unwrap();
    f.fail_error(f.claim_swap_ix(Some(1)), false, Some("Authority"));
    f.fail_error(f.claim_swap_ix(None), false, Some("Authority"));
    f.user = entitled;
    f.make_ata(f.r().room_mint, spl_token_2022_interface::ID);
    let mut wrong_ata = f.claim_swap_ix(Some(1));
    let recipient = ata(
        f.user.pubkey(),
        f.r().room_mint,
        spl_token_2022_interface::ID,
    );
    for account in &mut wrong_ata.accounts {
        if account.pubkey == recipient {
            account.pubkey = f.doors[1].user;
        }
    }
    f.fail_error(wrong_ata, false, Some("Account"));
    let before = f.balance(recipient);
    let sold = f.r().sold;
    let reserve = f.r().reserve;
    for door in [Some(1), None, Some(2), Some(0)] {
        f.claim_swap(door);
    }
    assert_eq!(f.balance(recipient) - before, charged);
    assert_eq!(f.r().swap_fees_unclaimed, 0);
    assert_eq!(f.swap_fee_balance(), 0);
    assert_eq!((f.r().sold, f.r().reserve), (sold, reserve));
    f.claim_swap(Some(1));
    f.claim_swap(None);
    assert_eq!(f.balance(recipient) - before, charged);
}

#[test]
fn paired_swaps_and_claims_cover_all_doors_unclaimed_fees() {
    let mut f = Fixture::new(0);
    f.open(launch("Other door liability"));
    f.open(launch("Current receiving door"));
    f.trade(Some(0), true, 5_050_000_000);
    f.swap(0, 1, f.balance(f.doors[0].user) / 2);
    f.swap(0, 2, f.balance(f.doors[0].user) / 2);
    f.make_ata(f.r().room_mint, spl_token_2022_interface::ID);
    let vault = p(&[b"swap_fees", f.room.as_ref()]);
    let original = f.svm.get_account(&vault).unwrap();
    let incomplete = f.r().protocol_accrued_room + f.d(2).accrued_room;
    assert!(incomplete < f.r().swap_fees_unclaimed);
    let mut underfunded = original.clone();
    underfunded.data[64..72].copy_from_slice(&incomplete.to_le_bytes());
    f.svm.set_account(vault, underfunded).unwrap();
    f.fail_error(
        f.swap_ix(0, 2, f.balance(f.doors[0].user) / 2),
        false,
        Some("Invariant"),
    );
    f.fail_error(f.claim_swap_ix(Some(2)), false, Some("Invariant"));
    f.fail_error(f.claim_swap_ix(None), false, Some("Invariant"));
    f.svm.set_account(vault, original).unwrap();
    f.audit();
    f.claim_swap(Some(1));
    f.claim_swap(Some(2));
    f.claim_swap(None);
    assert_eq!(f.r().swap_fees_unclaimed, 0);
}

#[test]
fn paired_swap_claims_follow_fee_recipient_changes() {
    let mut f = Fixture::new(0);
    f.open(launch("Changed fee recipient"));
    f.trade(Some(0), true, 1_010_000_000);
    f.swap(0, 1, f.balance(f.doors[0].user) / 2);
    let recipient = f.matcher.pubkey();
    let settings = defaults(f.matcher.pubkey(), recipient);
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
    let door = &f.doors[1];
    f.send(
        instr(
            a::SetRecipient {
                authority: f.user.pubkey(),
                core: f.core(),
                door: door.door,
                door_mint: door.mint,
                door_vault: door.vault,
                backing: door.backing,
            },
            ix::SetFeeRecipient {
                new_recipient: recipient,
            },
        ),
        false,
        "set_fee_recipient",
    );
    f.fail_error(f.claim_swap_ix(Some(1)), false, Some("Authority"));
    f.fail_error(f.claim_swap_ix(None), false, Some("Authority"));
    let charged = f.r().swap_fees_unclaimed;
    std::mem::swap(&mut f.user, &mut f.matcher);
    f.svm.airdrop(&f.user.pubkey(), 10_000_000).unwrap();
    f.claim_swap(Some(1));
    f.claim_swap(None);
    let recipient_token = ata(recipient, f.r().room_mint, spl_token_2022_interface::ID);
    assert_eq!(f.balance(recipient_token), charged);
    assert_eq!(f.r().swap_fees_unclaimed, 0);
    std::mem::swap(&mut f.user, &mut f.matcher);
    f.audit();
}

#[test]
fn paired_metadata_builder_matches_the_pinned_interface() {
    let mint = Pubkey::new_unique();
    let authority = Pubkey::new_unique();
    for (name, symbol, uri) in [
        ("Metadata".to_string(), "META".to_string(), String::new()),
        ("n".repeat(32), "S".repeat(10), "u".repeat(200)),
        (
            "\u{e9}".repeat(16),
            "\u{20ac}".repeat(3),
            format!("ipfs://{}", "\u{1f600}".repeat(48)),
        ),
    ] {
        let mut input = launch(&name);
        input.symbol = symbol;
        input.uri = uri;
        let actual = doors_v1::vaults::metadata_initialize_ix(
            &spl_token_2022_interface::ID,
            &mint,
            &authority,
            &input,
        );
        let expected = spl_token_metadata_interface::instruction::initialize(
            &spl_token_2022_interface::ID,
            &mint,
            &authority,
            &mint,
            &authority,
            input.name,
            input.symbol,
            input.uri,
        );
        assert_eq!(actual, expected);
    }
}
