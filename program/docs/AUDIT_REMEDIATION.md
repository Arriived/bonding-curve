# M-8, H-1 and M-6 remediation — 5 November 2026

Owner decisions: reduce creation CPIs first; apply the funded-wallet reservation
mitigation now; require an on-chain NameLock before mainnet; retain the shared
liveness gate with seven days' on-chain notice. Devnet funds remain upgrade budget.
No deployment or spending of that budget is part of this change.

## M-8 and M-7: creation path

Manual PDA creation uses System `CreateAccountAllowPrefund` for a prefunded,
system-owned, data-empty PDA. This preserves its existing lamports and transfers
only the missing rent, then allocates and assigns in one CPI. Canonical address,
owner and empty-data validation remain in place. Fresh accounts still use
`create_account`. Anchor's Room/Door account initializers are unchanged.

The instruction's SIMD-0312 gate was checked by read-only finalized RPC on
devnet and mainnet. Activation slots and observation slots are saved in
`verification/prefund_feature.json`. No larger heap or custom allocator is used.
The maximum-metadata prefunded takeover is now a required regression instead of
an ignored reproduction. The trace test requires successful launches and at
least ten spare entries, including a priority fee and two extra budget instructions.
Execution results must be recorded before either finding is marked resolved.

## H-1: interim service mitigation; mainnet remains blocked

Before reserving or signing a new room, the matcher reads the launcher's balance
and requires enough for all new-account rent, launch fees, requested first buy,
and the network fee quoted for the actual message (including its priority fee).
The cluster supplies rent minimums. Existing accounts and donations are not
credited to this conservative budget. A funding RPC failure refuses the decision.
The funding breakdown and balance observation slot are saved with the decision.

The launcher key, name and identity are acquired in one atomic in-flight claim.
One funded launcher can hold at most one new-room reservation. Signing/storage
failures release the entire claim; blockhash expiry prunes it. Door requests
continue independently. The request's existing wallet signature authenticates
the launcher before the HTTP endpoint reaches this pipeline.

This is a balance check, not a bond or escrow. Multiple funded wallets can still
squat, and process-local reservations still require a single replica. The
consolidation rule still depends on the operator's service: 9/16 audited routed
pairs have distinct SlugLocks. **An on-chain NameLock covering the matcher's
canonical name key is a mandatory mainnet blocker. This mitigation does not
close that program-level gap or make the current release mainnet-ready.**

## M-6: shared gate with a seven-day timelock

`update_config` rejects changes to any of the five liveness thresholds. The
initial Config setup remains unchanged; the deployed Config and Room byte
layouts are preserved.

`schedule_liveness` requires the current admin and writes the canonical
`pending_liveness` PDA with the full threshold set and `activate_at = Clock +
604800`. It emits `LivenessScheduled` with the old/new values and both times.
Replacing a schedule restarts the full delay. `cancel_liveness` requires the
current admin, invalidates the pending change and emits `LivenessCancelled`.

`apply_liveness` is permissionless at or after the recorded time. It updates the
one shared Config gate, consumes the schedule, and emits `LivenessApplied` plus
the existing `ConfigChanged` event for decision-verifier replay. Merely reaching
the timestamp does not apply the change: a transaction must execute it.
Unrelated Config updates preserve active thresholds and do not shorten the delay.
All routing, takeover and release paths keep reading the same active Config gate.

The program upgrade authority retains its existing power to replace this code;
this timelock constrains the Config-admin instruction path, not program upgrades.
