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

    for mut follower in followers {
        paired_actor(&mut f, &mut follower);
        let tokens = f.balance(f.doors[source].user);
        if rotate {
            f.swap(source, destination, tokens);
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
