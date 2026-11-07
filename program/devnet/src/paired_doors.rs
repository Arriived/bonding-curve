use anchor_lang::solana_program::system_instruction::transfer as transfer_sol;

const SOL: u64 = 1_000_000_000;

fn paired_spot(r: &Room) -> Result<f64> {
    let price = r.price()?;
    Ok(price.numerator as f64 / price.denominator as f64)
}

fn paired_snapshot(
    chain: &Chain,
    ctx: &Ctx,
    doors: &[DoorKeys],
    initial_price: f64,
    step: &str,
) -> Result<Value> {
    let (slot, account) = chain.account_at(&ctx.room)?;
    let account = account.ok_or_else(|| anyhow!("room is missing"))?;
    let room = Room::try_deserialize(&mut &account.data[..])?;
    let room_price = paired_spot(&room)?;
    let base = doors_v1::math::DOOR_VIRTUAL_BASE as f64;
    let mut faces = Vec::new();
    for (index, keys) in doors.iter().enumerate() {
        let (read_slot, account) = chain.account_at(&keys.door)?;
        let account = account.ok_or_else(|| anyhow!("door {} is missing", keys.door))?;
        let door = Door::try_deserialize(&mut &account.data[..])?;
        let spot = base * door.virtual_quote as f64 / (base - door.sold as f64).powi(2);
        faces.push(json!({"index": index, "slot": read_slot, "fdv_sol": spot * room_price * U as f64 / SOL as f64,
                          "sold_base": door.sold, "room_reserve_base": door.backing}));
    }
    Ok(
        json!({"step": step, "slot": slot, "room_price_multiple": room_price / initial_price,
              "room_sold_base": room.sold, "room_reserve_lamports": room.reserve, "doors": faces}),
    )
}

fn paired_open(
    chain: &mut Chain,
    ctx: &Ctx,
    launcher: &Keypair,
    matcher: &Keypair,
    name: &str,
    nonce: u64,
    first_buy: u64,
) -> Result<()> {
    let mut input = launch(name, "PAIR");
    input.uri = "https://example.invalid/p.json".into();
    input.first_buy_lamports = first_buy;
    let input = prepare(chain, input, nonce)?;
    let ix = ctx.open_ix(
        &chain.room(&ctx.room)?,
        launcher.pubkey(),
        matcher.pubkey(),
        input,
    );
    chain.send("open_door", &[ix], launcher, &[matcher])?;
    Ok(())
}

fn paired_trade(
    chain: &mut Chain,
    ctx: &Ctx,
    keys: &DoorKeys,
    owner: &Keypair,
    buy: bool,
    amount: u64,
) -> Result<Value> {
    let ix = ctx.trade_ix(
        &chain.room(&ctx.room)?,
        owner.pubkey(),
        Some(keys),
        buy,
        amount,
    );
    chain.send(
        if buy { "buy_door" } else { "sell_door" },
        &[ix],
        owner,
        &[],
    )
}

fn paired_unrelated_dump(
    chain: &mut Chain,
    ctx: &Ctx,
    source: &DoorKeys,
    keeper: &Keypair,
) -> Result<()> {
    let r = chain.room(&ctx.room)?;
    let spot = paired_spot(&r)?;
    let needed = ((r.v_tok - r.sold) as f64 * (2.0_f64.sqrt() - 1.0)).round() as u64;
    let d = chain.door(&source.door)?;
    let integral = doors_v1::math::door_integral(d.virtual_quote, d.sold)?;
    anyhow::ensure!(integral >= needed, "unrelated holder cannot cover the dump");
    let (mut lo, mut hi) = (0, chain.balance(&ata(keeper.pubkey(), source.mint, T22))?);
    while hi - lo > 1 {
        let mid = lo + (hi - lo) / 2;
        let out = integral - doors_v1::math::door_integral(d.virtual_quote, d.sold - mid)?;
        if out >= needed {
            hi = mid;
        } else {
            lo = mid;
        }
    }
    paired_trade(chain, ctx, source, keeper, false, hi)?;
    anyhow::ensure!(
        (paired_spot(&chain.room(&ctx.room)?)? / spot - 0.5).abs() < 1e-6,
        "unrelated room dump did not halve the price"
    );
    Ok(())
}

fn paired_cleanup(
    chain: &mut Chain,
    ctx: &Ctx,
    doors: &[DoorKeys],
    wallets: &[&Keypair],
    payer: &Keypair,
) -> Result<()> {
    for wallet in wallets {
        let owner = wallet.pubkey();
        for keys in doors {
            let address = ata(owner, keys.mint, T22);
            if chain.account_at(&address)?.1.is_none() {
                continue;
            }
            let held = chain.balance(&address)?;
            if held > 0 {
                paired_trade(chain, ctx, keys, wallet, false, held)?;
            }
            let close = spl_token_2022_interface::instruction::close_account(
                &T22,
                &address,
                &payer.pubkey(),
                &owner,
                &[],
            )?;
            chain.send("reclaim_empty_test_ata", &[close], wallet, &[])?;
        }
        let balance = chain
            .account_at(&owner)?
            .1
            .map_or(0, |account| account.lamports);
        if balance == 0 {
            continue;
        }
        let preview = chain.tx(&[transfer_sol(&owner, &payer.pubkey(), 1)], wallet, &[])?;
        let message = b64_encode(&preview.message_data());
        let fee = chain.rpc(
            "getFeeForMessage",
            json!([message, {"commitment": "confirmed"}]),
        )?["value"]
            .as_u64()
            .ok_or_else(|| anyhow!("sweep fee unavailable"))?;
        if let Some(amount) = balance.checked_sub(fee).filter(|amount| *amount > 0) {
            chain.send(
                "sweep_test_wallet",
                &[transfer_sol(&owner, &payer.pubkey(), amount)],
                wallet,
                &[],
            )?;
        }
    }
    Ok(())
}

fn paired_wallets(dir: &str) -> Result<Vec<Keypair>> {
    let mut wallets = vec![key(dir, "smoke-launcher")?, key(dir, "smoke-trader")?];
    for i in 1..=20 {
        wallets.push(key(dir, &format!("follower-{i:02}"))?);
    }
    Ok(wallets)
}

fn paired_checkpoint(out: &str, report: Value) -> Result<()> {
    let tmp = format!("{out}.tmp");
    fs::write(&tmp, serde_json::to_vec_pretty(&report)?)?;
    fs::rename(tmp, out)?;
    Ok(())
}

fn paired_payer_balance(chain: &Chain, payer: &Keypair) -> Result<Value> {
    chain.rpc(
        "getBalance",
        json!([payer.pubkey().to_string(), {"commitment": "finalized"}]),
    )
}

fn resume_paired_cleanup(dir: &str, interrupted_report: &str, out: &str) -> Result<()> {
    anyhow::ensure!(
        !std::path::Path::new(out).exists(),
        "use a fresh cleanup report path"
    );
    let previous: Value = serde_json::from_slice(&fs::read(interrupted_report)?)?;
    anyhow::ensure!(
        previous["program"] == ID.to_string(),
        "report program mismatch"
    );
    let active = &previous["active_case"];
    let room_id = active["room_id"]
        .as_u64()
        .ok_or_else(|| anyhow!("no active case"))?;
    let ctx = Ctx::new(room_id);
    anyhow::ensure!(
        active["room"] == ctx.room.to_string(),
        "report room mismatch"
    );
    let nonces = active["door_nonces"]
        .as_array()
        .ok_or_else(|| anyhow!("missing door nonces"))?;
    let doors = nonces
        .iter()
        .map(|nonce| {
            Ok(DoorKeys::new(
                ctx.room,
                nonce.as_u64().ok_or_else(|| anyhow!("invalid nonce"))?,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let mut chain = Chain::new();
    let payer = key(dir, "deploy-wallet")?;
    let wallets = paired_wallets(dir)?;
    let wallets = wallets.iter().collect::<Vec<_>>();
    let result = paired_cleanup(&mut chain, &ctx, &doors, &wallets, &payer);
    paired_checkpoint(
        out,
        json!({
            "program": ID.to_string(), "active_case": active, "transactions": chain.log,
            "payer_balance": paired_payer_balance(&chain, &payer).ok(),
            "error": result.as_ref().err().map(ToString::to_string),
        }),
    )?;
    result
}

fn run_paired(dir: &str, out: &str) -> Result<()> {
    anyhow::ensure!(
        !std::path::Path::new(out).exists(),
        "use a fresh report path for a new run"
    );
    let mut chain = Chain::new();
    let payer = key(dir, "deploy-wallet")?;
    let matcher = key(dir, "matcher-authority")?;
    let wallets = paired_wallets(dir)?;
    let keeper = &wallets[0];
    let trader = &wallets[1];
    let followers = &wallets[2..];
    let wallets = wallets.iter().collect::<Vec<_>>();
    let config = Config::try_deserialize(&mut &chain.account(&p(&[b"config"]))?.data[..])?;
    let expected: Value = serde_json::from_str(include_str!(
        "../../../research/doors_into_one_room/outputs/curve_quantities.json"
    ))?;
    anyhow::ensure!(
        config.v_sol_lamports == expected["v_sol_lamports"].as_u64().unwrap()
            && config.v_tok == expected["v_tok_base"].as_u64().unwrap()
            && config.graduation_trigger_lamports == expected["trigger"].as_u64().unwrap()
            && config.fee_bps == 100
            && config.door_share_bps == 6_000
            && config.founder_share_bps == 0
            && config.door_fee_lamports == 0
            && config.room_fee_lamports == 0
            && config.matcher_authority == matcher.pubkey(),
        "devnet benchmark requires the unchanged default room settings"
    );

    let setup = chain.rent(2048)? * 16;
    let follower_allowance = chain.rent(256)? * 2 + chain.rent(0)? + 50_000;
    let mut results = Vec::new();
    let mut active = Value::Null;
    let result: Result<()> = (|| {
        for seed in [50, 10, 0] {
            for dump in [false, true] {
                if seed == 0 && dump {
                    continue;
                }
                for rotate in [false, true] {
                    let id = door_nonce()?;
                    let tag = format!("{id:016x}");
                    let ctx = Ctx::new(id);
                    let nonces = [0, door_nonce()?, door_nonce()?];
                    active = json!({"room_id": id, "room": ctx.room.to_string(), "door_nonces": nonces,
                                    "initial_room_sol": seed, "dump": dump, "followers_rotate": rotate});
                    paired_checkpoint(
                        out,
                        json!({
                            "program": ID.to_string(), "active_case": active, "cases": results, "transactions": chain.log,
                        }),
                    )?;
                    let budgets = [seed * 1_010_000_000 + setup, 2 * SOL + setup]
                        .into_iter()
                        .chain(std::iter::repeat_n(SOL + follower_allowance, 20));
                    let mut funding = Vec::new();
                    for (wallet, budget) in wallets.iter().zip(budgets) {
                        let balance = chain
                            .account_at(&wallet.pubkey())?
                            .1
                            .map_or(0, |a| a.lamports);
                        if let Some(amount) =
                            budget.checked_sub(balance).filter(|amount| *amount > 0)
                        {
                            funding.push(transfer_sol(&payer.pubkey(), &wallet.pubkey(), amount));
                        }
                    }
                    for batch in funding.chunks(8) {
                        chain.send("fund_test_wallets", batch, &payer, &[])?;
                    }

                    let mut start = launch(&format!("Room {tag}"), "PAIR");
                    start.uri = "https://example.invalid/p.json".into();
                    start.first_buy_lamports = seed * 1_010_000_000;
                    let start = prepare(&chain, start, 0)?;
                    chain.send(
                        "create_room",
                        &[ctx.create_ix(keeper.pubkey(), matcher.pubkey(), start)],
                        keeper,
                        &[&matcher],
                    )?;
                    let initial = chain.room(&ctx.room)?;
                    let initial_price = paired_spot(&initial)?;
                    anyhow::ensure!(initial.reserve == seed * SOL, "unexpected seed reserve");
                    paired_open(
                        &mut chain,
                        &ctx,
                        keeper,
                        &matcher,
                        &format!("Rotate {tag}"),
                        nonces[1],
                        0,
                    )?;
                    paired_open(
                        &mut chain,
                        &ctx,
                        trader,
                        &matcher,
                        &format!("Follow {tag}"),
                        nonces[2],
                        2 * SOL,
                    )?;
                    let doors = nonces.map(|nonce| DoorKeys::new(ctx.room, nonce));
                    let mut steps = vec![paired_snapshot(
                        &chain,
                        &ctx,
                        &doors,
                        initial_price,
                        "after_a_buys",
                    )?];
                    for wallet in followers {
                        let owner = wallet.pubkey();
                        let setup = [
                            create_ata_ix(owner, owner, doors[2].mint, T22),
                            create_ata_ix(owner, owner, doors[1].mint, T22),
                        ];
                        chain.send("create_follower_atas", &setup, wallet, &[])?;
                        paired_trade(&mut chain, &ctx, &doors[2], wallet, true, SOL)?;
                    }
                    steps.push(paired_snapshot(
                        &chain,
                        &ctx,
                        &doors,
                        initial_price,
                        "after_followers_buy",
                    )?);
                    if dump {
                        paired_unrelated_dump(&mut chain, &ctx, &doors[0], keeper)?;
                        steps.push(paired_snapshot(
                            &chain,
                            &ctx,
                            &doors,
                            initial_price,
                            "after_unrelated_room_dump",
                        )?);
                    }
                    let a_tokens = chain.balance(&ata(trader.pubkey(), doors[2].mint, T22))?;
                    let a_exit =
                        paired_trade(&mut chain, &ctx, &doors[2], trader, false, a_tokens)?;
                    let trade = trades_in(&a_exit)
                        .into_iter()
                        .next()
                        .ok_or_else(|| anyhow!("late-buyer sale event missing"))?;
                    let payout = trade.curve_lamports - trade.fee;
                    steps.push(paired_snapshot(
                        &chain,
                        &ctx,
                        &doors,
                        initial_price,
                        "after_a_exits",
                    )?);
                    for wallet in followers {
                        let tokens = chain.balance(&ata(wallet.pubkey(), doors[2].mint, T22))?;
                        if rotate {
                            let ix = ctx.swap_ix(
                                &chain.room(&ctx.room)?,
                                wallet.pubkey(),
                                &doors[2],
                                &doors[1],
                                tokens,
                            );
                            chain.send("swap_doors", &[ix], wallet, &[])?;
                        } else {
                            paired_trade(&mut chain, &ctx, &doors[2], wallet, false, tokens)?;
                        }
                    }
                    let exit = if rotate {
                        "after_followers_rotate"
                    } else {
                        "after_followers_cash_out"
                    };
                    steps.push(paired_snapshot(&chain, &ctx, &doors, initial_price, exit)?);
                    results.push(json!({"initial_room_sol": seed, "dump": dump,
                        "followers_rotate": rotate, "room": ctx.room.to_string(),
                        "a_payout_lamports": payout, "a_exit": a_exit, "steps": steps}));
                    paired_cleanup(&mut chain, &ctx, &doors, &wallets, &payer)?;
                    active = Value::Null;
                    paired_checkpoint(
                        out,
                        json!({
                            "program": ID.to_string(), "active_case": active, "cases": results, "transactions": chain.log,
                        }),
                    )?;
                }
            }
        }
        Ok(())
    })();
    paired_checkpoint(
        out,
        json!({
            "program": ID.to_string(), "active_case": active, "cases": results, "transactions": chain.log,
            "payer_balance": paired_payer_balance(&chain, &payer).ok(),
            "error": result.as_ref().err().map(ToString::to_string),
        }),
    )?;
    result
}
