fn schedule_gate(f: &mut Fixture, thresholds: LivenessThresholds) -> TransactionMetadata {
    f.send(
        instr(
            a::ScheduleLiveness {
                admin: f.user.pubkey(),
                config: f.cfg,
                pending: p(&[b"pending_liveness"]),
                system_program: anchor_lang::system_program::ID,
            },
            ix::ScheduleLiveness { thresholds },
        ),
        false,
        "schedule_liveness",
    )
}
fn apply_gate(f: &Fixture) -> Instruction {
    instr(
        a::ApplyLiveness {
            config: f.cfg,
            pending: p(&[b"pending_liveness"]),
        },
        ix::ApplyLiveness {},
    )
}
fn cancel_gate(f: &Fixture) -> Instruction {
    instr(
        a::CancelLiveness {
            admin: f.user.pubkey(),
            config: f.cfg,
            pending: p(&[b"pending_liveness"]),
        },
        ix::CancelLiveness {},
    )
}

#[test]
fn all_five_liveness_thresholds_reject_immediate_config_changes() {
    let mut f = Fixture::empty(0);
    for field in 0..5 {
        let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
        match field {
            0 => settings.live_min_reserve_lamports += 1,
            1 => settings.live_max_idle_seconds += 1,
            2 => settings.live_new_seconds += 1,
            3 => settings.live_min_volume_lamports += 1,
            _ => settings.pool_min_window_lp_fee += 1,
        }
        let before = f.svm.get_account(&f.cfg).unwrap().data;
        let ix = instr(
            a::UpdateConfig {
                admin: f.user.pubkey(),
                config: f.cfg,
            },
            ix::UpdateConfig {
                settings,
                new_admin: f.user.pubkey(),
            },
        );
        f.fail_error(ix, false, Some("LivenessTimelock"));
        assert_eq!(before, f.svm.get_account(&f.cfg).unwrap().data);
    }
}

#[test]
fn liveness_change_preserves_the_shared_gate_for_a_full_seven_days() {
    use anchor_lang::Discriminator;
    use base64::Engine;
    let mut f = Fixture::new(0);
    let before = f.c().liveness();
    let mut changed = before;
    changed.live_min_reserve_lamports = u64::MAX;
    // Prefunding the pending PDA must not block governance either.
    let pending = p(&[b"pending_liveness"]);
    let rent = f.svm.minimum_balance_for_rent_exemption(0);
    f.svm.airdrop(&pending, rent).unwrap();
    let meta = schedule_gate(&mut f, changed);
    assert!(meta
        .logs
        .iter()
        .filter_map(|line| line.strip_prefix("Program data: "))
        .filter_map(|s| base64::engine::general_purpose::STANDARD.decode(s).ok())
        .any(|data| data.starts_with(doors_v1::LivenessScheduled::DISCRIMINATOR)));
    assert_eq!(f.c().liveness(), before);
    let queued =
        PendingLiveness::try_deserialize(&mut &f.svm.get_account(&pending).unwrap().data[..])
            .unwrap();
    assert_eq!(
        queued.activate_at,
        f.svm.get_sysvar::<Clock>().unix_timestamp + 604_800
    );
    f.time(LIVENESS_CHANGE_DELAY_SECONDS - 1);
    f.trade(Some(0), true, 10_100_000_000);
    assert!(f
        .r()
        .live(&f.c(), f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    f.fail_error(apply_gate(&f), false, Some("LivenessDelay"));
    assert_eq!(f.c().liveness(), before);
    f.time(1);
    // A fee payer distinct from the Config admin can apply a matured change.
    std::mem::swap(&mut f.user, &mut f.matcher);
    f.send(apply_gate(&f), false, "apply_liveness");
    assert_eq!(f.c().liveness(), changed);
    assert!(!f
        .r()
        .live(&f.c(), f.svm.get_sysvar::<Clock>().unix_timestamp)
        .unwrap());
    f.fail_error(apply_gate(&f), false, Some("NoPendingLiveness"));
}

#[test]
fn liveness_rescheduling_restarts_the_delay_and_cancellation_invalidates_it() {
    let mut f = Fixture::empty(0);
    let before = f.c().liveness();
    let mut changed = before;
    changed.live_new_seconds += 1;
    schedule_gate(&mut f, changed);
    f.time(LIVENESS_CHANGE_DELAY_SECONDS - 1);
    changed.live_min_volume_lamports += 1;
    schedule_gate(&mut f, changed);
    f.time(1);
    f.fail_error(apply_gate(&f), false, Some("LivenessDelay"));
    f.send(cancel_gate(&f), false, "cancel_liveness");
    f.time(LIVENESS_CHANGE_DELAY_SECONDS);
    f.fail_error(apply_gate(&f), false, Some("NoPendingLiveness"));
    assert_eq!(f.c().liveness(), before);
}

#[test]
fn only_current_admin_can_schedule_or_cancel_liveness() {
    let mut f = Fixture::empty(0);
    let mut thresholds = f.c().liveness();
    thresholds.live_new_seconds += 1;
    let wrong = instr(
        a::ScheduleLiveness {
            admin: f.matcher.pubkey(),
            config: f.cfg,
            pending: p(&[b"pending_liveness"]),
            system_program: anchor_lang::system_program::ID,
        },
        ix::ScheduleLiveness { thresholds },
    );
    f.fail_error(wrong, true, None);
    schedule_gate(&mut f, thresholds);
    let wrong = instr(
        a::CancelLiveness {
            admin: f.matcher.pubkey(),
            config: f.cfg,
            pending: p(&[b"pending_liveness"]),
        },
        ix::CancelLiveness {},
    );
    f.fail_error(wrong, true, None);
    f.time(LIVENESS_CHANGE_DELAY_SECONDS);
    f.send(apply_gate(&f), false, "apply_liveness");
    assert_eq!(f.c().liveness(), thresholds);
}
