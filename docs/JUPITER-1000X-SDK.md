# Jupiter 1000x SDK and order groundwork

Version: 1.1.0. Delta: distinguish interface terms and full-corpus review from the initial SDK slice, 2026-11-16.

The indicator overlay is read-only. This document prepares a later execution
design; it does not enable signing, submission, arming, or autonomous trading.
The existing executor remains restricted to BTC and ZEC. SOL market-data
availability does not grant SOL execution support.

## Evidence and scope

The official developer snapshot at
/Users/mitch/.local/state/jup1000x-overlay-2348/jupiter-llms-full.txt contains
1,182,340 bytes, 27,452 lines and 243 `Source:` sections. All sections were
inventoried. This SDK slice reviewed Development Basics, Environment Setup,
the complete SDK & API License Agreement, all five Perps overview/account
pages, and Jupiter Tool Kits. That initial pass did not review every unrelated
developer page. Its inventory and exact reviewed ranges are in
/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/developer-sections.json
and /Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/docs-review.json.

Three separate reviewers then read all 27,452 lines in bounded sections, with
no remaining gaps or unrepaired truncation. The combined receipt is
/Users/mitch/.local/state/jup1000x-overlay-2348/docs-full-review/coverage.json.
The snapshot SHA-256 is `28db4e6df245eea4ef85336a6740fef9db4c5420c11a462238917312f116e873`.
This is complete review of the supplied snapshot; unexpanded OpenAPI references
and linked repositories are not automatically included. The broader review
found no 1000x feed or position create/close contract. RFQ streaming, Trigger
authentication, Lend units and Plugin `close()` belong to separate products.

The developer Perps overview calls its API a work in progress and describes
the JLP program, `PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu`.
That contract does not establish 1000x support. Current official user docs
describe 1000x separately, against the House, and say YOLO was renamed 1000x
on November 11, 2026. Old YOLO documentation URLs currently redirect to these
1000x pages:

https://developers.jup.ag/docs/perps/index

https://docs.jup.ag/user-docs/trade/1000x.md

https://docs.jup.ag/user-docs/trade/1000x/trading.md

https://docs.jup.ag/user-docs/trade/1000x/faq.md

The installed `jupiter-sdk` is pinned to **0.6.0**, imported through
`jupiter-sdk/yolo/web3js`. Its README explicitly says it is an independent,
community-maintained package, not an official Jupiter package. The package's
`author` metadata does not override that disclaimer. Its repository is:

https://github.com/ChiefWoods/jupiter-sdk

The package declares MIT licensing. Jupiter's separate API agreement describes
swap routing and imposes its own usage, redistribution and other restrictions;
an MIT package license does not establish permission or a compatibility promise
for the portal service. Applicability to a future distributed 1000x integration
remains unresolved by this engineering review:

https://developers.jup.ag/docs/legal/sdk-api-license-agreement

The separate Interface terms define the Interface as `https://jup.ag`, restrict
copying and reverse engineering, list prohibited wallet localities, and forbid
network or VPN circumvention. This engineering review does not establish user
eligibility or resolve how those clauses apply to a distributed 1000x adapter.
It provides no permission to bypass access controls. Exact source spans are in
the local full-corpus review, including lines 4088–4197 of the archived snapshot:

https://developers.jup.ag/docs/legal/terms-of-use

Current public frontend text identifies the separate 1000x program
`yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA` and service
https://yolo-api.jup.ag

Observed HTTP schemas are portal internals, with no published external
compatibility guarantee found in the reviewed developer pages. No POST, wallet
or user-account read, RPC account read, signature, simulation, or transaction
was performed in this SDK review. Public GET `/markets` and unsigned offline
constructor fixtures supplied the direct checks below.

## Current capability matrix

| Capability | Verified scope and boundary |
| --- | --- |
| Markets | Public GET `/markets` returned BTC, SOL, ETH, ZEC, HYPE, XAU and WTI; the UI labels XAU as GOLD and WTI as OIL. SOL has feed ID `6` and market address `Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS`. This is a dated service snapshot, not an on-chain account verification. |
| Existing execution adapter | `/Users/mitch/dev/solmargintrader/oracle_leverage/sdk/bridge.mjs:66` and `/Users/mitch/dev/solmargintrader/oracle_leverage/sdk/service.mjs:9` allow BTC/ZEC only. Neither adapter was expanded. |
| Classic actions | Official user docs describe market opens and whole-position closes. No partial close, collateral adjustment, user stop loss or user limit order. Raw constructors encode open/close; they do not prove economic validity or an executable fill. |
| Other portal modes | Official docs describe Double or Nothing and Blitz. Current bundle schemas expose `targetBps` and `closeAfterSecs` through special build actions. These modes are outside the existing adapter and this groundwork; a mode-specific position must not be manually closed as Classic. |
| Leverage | Official UI offers 500–1,000 in steps of 100. The bundle's final open validation caps leverage at 1,000. Existing bridge/service intent validation accepts exactly 1,000. The SDK's `u16` encoding alone does not enforce these limits. |
| Collateral | JupUSD, mint `JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD`. The portal can swap another input token; the current bridge builds the direct JupUSD path. Do not infer swap support from a generic Jupiter swap API. |
| Current minimum and capacity | Snapshot `minMargin="5000000"` means 5 JupUSD. `maxPositionOi` is `1000000000000` micro units for BTC/SOL/ETH and `250000000000` for ZEC/HYPE/XAU/WTI. Market-side capacity, pauses, close-only flags and trading hours must be refreshed before any future plan. |
| Fees | Snapshot `closeFeePpm=20` and `winFeePpm=30000`: close fee is 0.002% of notional; win fee is 3% of adjusted positive profit. At 1,000x, that close fee is 2% of initial collateral. Profitable outcomes use a nonlinear adjustment and a 25× adjusted-profit cap; do not model them as plain linear leveraged returns. SOL network fees and rent are additional. Official docs say there is no borrow/funding/holding fee. Refresh fee fields; these values are not permanent defaults. |
| Owner and keeper | Both SDK manual open and close constructors mark the owner and keeper as signers. Public docs say the trade service co-signs manual actions. Keeper-triggered automatic closes are a separate path and need no owner signature. A local owner signature cannot replace keeper authorization. |
| Price provenance | Official docs say chart/estimated prices are indicative Pyth prices; opens and closes fill at Pyth Pro recorded on-chain about two seconds after submission, with no price limit. A displayed indicator price is not an order quote, guaranteed fill, or slippage bound. |
| Freshness | SDK config exposes `maxOracleAgeSecs`, `maxOracleFutureSecs`, and `maxRequestExecutionSec`. Their deployed values were not read. Existing verifier enforces request age at most `min(30, configured maxRequestExecutionSec)` seconds, rejects more than two seconds into the future, and checks blockhash plus last-valid block height. User docs describe a 20-second execution expiry. These are different source scopes; do not guess deployed config from either one. |
| Close cooldown and maximum hold | Docs specify earliest Classic close after 15 seconds and automatic close after 24 hours; public markets returned `maxHoldSecs=86400`. Existing service guard checks 15 seconds since `updateTime`; current frontend adds a three-second display buffer. Never shorten these with a strategy setting. |
| Build binding | Portal build schemas return `serializedTxBase64`, `buildToken`, optional `positionId`, and `txMetadata` containing blockhash/last-valid block height. Owner signing must preserve the exact message and the original build token must accompany execute. A stale build must be discarded only after any prior submit is reconciled. |
| Transaction versions | Current portal supports wallet-compatible v0/v1 messages. Existing bridge pins `@solana/web3.js` 1.98.4, requests v0, verifies v0 only and caps serialized bytes at 1,232. Portal acceptance of v1 does not extend that adapter. |
| Submit uncertainty | Execute schema has Processing/Completed/Failed and errors `execution_failed`/`execution_window_elapsed`. The portal reconciles `/requests/{txid}` and a separate confirmation route. Timeout, expiry wording or an empty cached position list alone cannot establish that no order executed. Preserve unknown state and never auto-resubmit it. |
| Payout queue | Closing and receiving profit are separate facts. Docs say remaining collateral returns at close; profit can wait in a FIFO House-funded queue indefinitely and payment is not guaranteed. Service user schema has `queued` and `claims`; SDK `DebtClaim` has sequence, owner, remaining balance and position ID. Execution `queuePosition` must not be treated as proof of a paid profit claim. |
| Simulation and sandbox | Raw bridge offers unsigned construction and explicit RPC simulation with `sigVerify:false`. This checks execution against available state without owner/keeper authentication; it does not prove a keeper will accept or co-sign. No funded simulation was run here. No supported 1000x devnet, paper exchange or sandbox contract was established; official FAQ says portal 1000x trades use real funds. |

Public market snapshot and fetch hashes:
/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/public-markets.json
and /Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/sources.json.

## Constructor contract and units

The installed generated declarations and codecs are the evidence for the exact
constructors; they are not an external service SDK or an oracle-price source.

| Constructor | Inputs | Output and units |
| --- | --- | --- |
| `createOpenPositionInstruction(accounts, args, programId?)` | Accounts: owner, keeper, market, JupUSD mint/funding account, oracle, token/system programs, event authority, program; config/pool/position/vault can be PDA-derived. Args: `id:u64`, `requestTime:i64`, `margin:u64`, `leverage:u16`, `long:bool`. | Promise of unsigned `TransactionInstruction`; 14 account metas, two signer metas, 35 data bytes. `id` is a position identifier; `requestTime` is UNIX seconds; `margin` is microJupUSD; leverage is a whole-number multiplier and `long` gives direction. Position PDA derives from owner and ID. No entry price is supplied by this constructor. |
| `createClosePositionInstruction(accounts, {requestTime}, programId?)` | Same shared program accounts, existing owned/open position, verified claim account and JupUSD destination; `requestTime:i64` in UNIX seconds. The claim sequence/PDA must be verified, never guessed. | Promise of unsigned `TransactionInstruction`; 15 account metas, two signer metas, 16 data bytes. It closes the entire position and carries no quantity or price argument. It does not prove immediate profit payment. |
| `parseOpenPositionInstruction` / `parseClosePositionInstruction` | A constructed instruction. | Decoded fields and account metas for comparison against the intended owner, program, market, direction, margin, leverage, time and destination. Parsing alone is not authorization or semantic verification. |

Use decimal strings over JSON and BigInt for integer arithmetic. Monetary
position fields `margin`, `notional`, realized PnL, paid and queued amounts use
10^6 units per JupUSD. Current portal position/trade `entryPrice`, `exitPrice`
and `price` use **10^12 fixed-point USD units**, independently of the market
feed's own exponent. Position timestamps use seconds; convert to milliseconds
only at a display boundary. Avoid floating-point round trips for order fields.

Source declarations/codecs are at
/Users/mitch/dev/solmargintrader/oracle_leverage/sdk/node_modules/jupiter-sdk/src/products/yolo/dist/web3js/index.d.ts:237
and
/Users/mitch/dev/solmargintrader/oracle_leverage/sdk/node_modules/jupiter-sdk/src/products/yolo/dist/web3js/index.js:1010.
Source hashes are recorded in
/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/installed-source-manifest.json.

## Later lifecycle and unresolved activation gates

1. Reconcile the venue's current positions, claims and any previous signature
   before planning another action. Preserve `unknown` for ambiguous submits.
2. Read current market state, fees, capacity, collateral decimals and program
   config. Reject stale/missing/NaN inputs, unavailable or close-only markets,
   invalid units, insufficient collateral, and unsupported modes or assets.
3. Build the exact open or owned Classic close through a verified interface.
   Validate program/account ownership, oracle/keeper authority, PDA derivations,
   all instructions, destinations, economic intent and bounded network fees.
   Keep the build token and message hash bound to that one intent.
4. Simulate the exact proposed bytes where supported. An unsigned successful
   simulation does not establish signer authorization, keeper availability or
   a fill. Check request/oracle age and block-height expiry again at signing.
5. Only after separate explicit activation authorization, obtain the owner
   signature and submit once with the original build token. Reconcile by the
   owner-derived transaction ID, chain status and fresh venue position state;
   never auto-retry an unknown action. Track closed-position settlement and
   unpaid-profit claims separately.

The current source already records a concrete blocker. In
/Users/mitch/dev/solmargintrader/oracle_leverage/sdk/service.mjs:108,
`inspectOpenBuild` can inspect the observed `UpdatePrice` + `OpenPosition`
shape and run unsigned simulation, but explicitly says it cannot establish
the service keeper authorization and that Submit is disabled. The stricter
`verifyBuild` path requires the keeper from program config and one allowed
trade instruction. Its supported shape cannot be broadened merely to make a
current service transaction pass. This review did not call the build endpoint,
verify an actual account, or resolve that gap.

Bridge status reports `serviceSubmitAvailable:true` because a service handler
exists. That static flag does not certify service verification, a funded fill,
or readiness for autonomous trading. Future work must resolve the keeper/price
update contract with independent evidence, add market-specific verification
before enabling SOL, exercise unknown-submit recovery and payout accounting,
and obtain separate live activation authorization. Keep extension defaults
dry-run/disarmed and preserve its existing risk and command registries.

## Verification receipt and source bindings

On 2026-11-16, the installed bridge `status` request exited 0. Offline synthetic
fixtures exited 0 for both SDK constructors and parsers, exact byte/account
counts, two signer metas, and refusals for SOL adapter execution, below-minimum
margin, owner-as-keeper and a missing close-claim PDA. The fixtures made zero
network calls and created zero signatures. This demonstrates encoding and
those refusal paths, not deployed account validity, keeper acceptance or a fill.

/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/bridge-status.json

/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/sdk-fixture-check.json

/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/check-sdk.mjs

Current portal bundle sources for schemas, message/build-token binding,
reconciliation, the 18-second display guard, and 10^12 price scaling:

https://jup.ag/assets/vendor-tanstack-runtime-D7h0586w.js

https://jup.ag/assets/DegenWatchMobile-BA7LHJXD.js

Exact Unicode offsets, quotes and SHA-256 hashes are retained outside Git at
/Users/mitch/.local/state/jup1000x-overlay-2348/sdk-notes/portal-spans.json.
The older observation at
/Users/mitch/dev/solmargintrader/docs/ORACLE-JUPITER-1000X-CONTRACT.md
is useful historical context; its two-market table is not the current full
catalog. Vendor bundles and downloaded documentation remain outside Git.
