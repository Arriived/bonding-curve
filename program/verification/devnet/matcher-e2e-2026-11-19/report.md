# Matcher devnet end-to-end passed, 19 November 2026

A real signed launch created a room, then identity-floor and name-matched requests opened doors into that room. All three transactions finalized successfully and received their exact quoted door-token amounts. The independent verifier agreed with every decision. An altered signed request was refused live before signing or recording a decision. Cleanup and the balance/rent/fee reconciliation passed. No mismatch or unexpected refusal occurred.

Program: `8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ`, deployment slot 520,996,477, ELF SHA-256 `fc2d615e37c63710326e18a29d157b50b0ad678ef9083e3161007bf43e8e9002`. Program hash and production Config still match after cleanup. No deployment or Config update was performed.

## Signer discovery and execution

The original files were found in the desktop application's virtualized local cache. The admin/upgrade, treasury/fee-recipient, matcher and both test-wallet public keys were derived locally and matched the expected identities before any signing. Files were read in place outside the repository and synced folders. No keyfiles or private signing material are in this evidence. The admin key was used only to verify its public identity.

The prepared `a7aa8c0` client is byte-identical to the requested version. Its API transport uses a real loopback HTTP matcher instance. The routing, quote, authentication, signing and transaction-building code is unchanged. Requests use 100,000,000 lamports per first buy, 200-bps slippage, the 500,000-CU limit and cu_price 1 micro-lamport/CU. The existing development E2E freshness budget is 30-slot coherence, 60-slot lag and 15-second age. The service uses the verified local matcher keyfile.

Run timestamps: 2026-11-19T03:22:07.592690+00:00 through 2026-11-19T03:34:38.915926+00:00. The run folder retains its 18 November preparation date; all funded execution occurred on 19 November.

## Signed transactions and independent verdicts

| Decision | Rule | Signature | Finalized slot | Quoted = received door base units | Transaction CU | Fee lamports | Verifier |
|---|---|---|---:|---:|---:|---:|---|
| signed_new_room | new_room | `3QNqjcw7vnvgFuZ3fa1Gb2wPJ1Jess1y2grs9akBa3w4N7HAcxUe22viVoPky8xU67yq9nkJUCWGyoqpp8TESLr3` | 523854267 | 3,518,117,069,295 | 310,898 | 10,001 | AGREE |
| signed_floor_door | floor | `4HhvL5SLHbisjhNbcSi3PM56MUaMsXhzUVwSNYEW6xnMNpsBoUcQ7Hyx8bbksgL3AN3UBJDJpbeAnSnYinBAJMm8` | 523854322 | 3,518,154,975,707 | 233,623 | 10,001 | AGREE |
| signed_name_door | T2n | `4uGyEjAXRwTNxij7yPp9KYXpZpFNN11uPPkkGP9rjZBVPLEL5mMjRXKCvSDuemyMz1FtPsH2TtReBdiBbkYXgXfT` | 523854377 | 3,518,192,669,439 | 215,577 | 10,001 | AGREE |

The room is `6JuEWEXkWMdbRuG97cJtTQtasMagQnkTrHSt8QnZzr3d` (ID `7728968838714237897`). The second and third decisions were signed after that room already existed on devnet. All three actual fills equal the snapshot quote exactly; each message carries a positive slippage-derived pre-settlement reserve bound and door-token minimum.

The verifier ran in process 2112, separate from service/client process 30780, using byte-identical verifier source `310e12a`. It loaded records from the database, checked the hash chain itself, then replayed 435 historical transactions from devnet. Service and signer modules were absent from the verifier process. The original client received the worker's actual checks/landed results; the independently saved worker results match them exactly. Its transaction cache contains only immutable responses at or below finalized root 523854395; mutable accounts were re-read. [Full independent checks](independent-verifier.json) and [source/transport provenance](runner-provenance.json).

## Live refusal

Before the valid new-room request, the HTTP adapter appended ` x` to the already-signed name and kept its original signature. The live matcher returned **401 `unauthenticated`**. Decision-row count remained **0 → 0**, and no transaction was returned or submitted. This refusal has no transaction signature, slot or execution fee. The original unaltered signed request was accepted immediately afterward. [Refusal request and response](live-refusal.json).

## Sweep and exact cost

| Item | Lamports | SOL |
|---|---:|---:|
| Opening treasury | 63,089,376,282 | 63.089376282 |
| Closing treasury | 63,046,940,822 | 63.046940822 |
| Incremental E2E cost | 42,435,460 | 0.042435460 |
| Retained new-account rent | 42,255,440 | 0.042255440 |
| Retained balances above rent | 0 | 0.000000000 |
| Network fees | 180,020 | 0.000180020 |

Opening read: finalized slot 523854133; closing read: finalized slot **523857921**. No external funding arrived during the run. Funding float was 1.2 SOL; positions, entitled fees, empty ATAs and remaining native balances were recovered. Both used test wallets are zero. All 24 other known operating wallets remain zero, and all six Token-2022/classic-token ownership scans for the treasury and used test wallets are empty. The new room/door accounts remain on-chain at their rent minima; no surplus reserve balance remains. Existing deployment rent is excluded from this incremental cost.

The cost reconciles exactly: opening minus closing = 42,255,440 rent + 0 above rent + 180,020 fees = 42,435,460 lamports. [All 20 finalized funding, launch, claim, close and sweep signatures/slots](signatures.csv); [accounting and retained accounts](accounting.json).

## Validation and scope

The unchanged service suite passed 180/180 before funding. The HTTP and verifier adapters compiled and the full live run passed. Core client and verifier hashes match the requested commits. The previous unfunded missing-path preflight is separate and cost zero. No keyfiles were copied, and private RPC debug logs and the local SQLite file are excluded from publication; canonical decision records and hash-chain links are exported.

No graduation, lookup-table or maker work was performed. Graduation design is the next task and needs the owner's DAMM v2 versus DLMM ruling.
