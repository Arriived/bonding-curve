**Approved rent correction.** The old `(128 + bytes) × 6,960` model is stale. The owner approved `(128 + bytes) × 5,080` after direct rent-exemption RPC confirmation. These are `getMinimumBalanceForRentExemption` results, not account balances. The method has no context slot; finalized slot reads bracket each request.

| data bytes | raw minimum (lamports) | finalized slot before | finalized slot after |
|---|---|---|---|
| 0 | 650,240 | 464,037,171 | 464,037,172 |
| 165 | 1,488,440 | 464,037,175 | 464,037,178 |

Additional size checks are recorded at slots 464,036,284–464,036,304 in `outputs/narrative/current_rent.json`; the confirmation is in `rent_confirmation.json`. The current schema's derived totals are:

| quantity | old rate on revised schema | verified rate on revised schema |
|---|---|---|
| launch rent, lamports | 37,604,880 | 27,447,240 |
| graduation rent, lamports | 24,680,160 | 18,013,680 |

All current rent-dependent spec figures are regenerated. The trigger remains a Config value snapshotted into each Room; a later rent/default change does not rewrite an old room's curve or graduation trigger. Runtime graduation uses the rent sysvar, not this calibration coefficient.
