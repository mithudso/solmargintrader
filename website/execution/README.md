# Customer execution service

This private Worker signs Coinbase Advanced Trade requests with credentials supplied by the authenticated customer. It never accepts a customer's primary wallet key or uses an operator exchange account. The public Worker passes an authenticated account and wallet principal over the `USER_TRADE_EXECUTOR` service binding. D1 and the private Worker independently check that principal against the current stored user and grant.

Coinbase spot execution is implemented. Jupiter execution remains disabled; the bounded native-program simulation results and remaining gates are recorded in `jupiter-qualification.json`. A successful local provider fixture or native request simulation does not establish production order acceptance or a completed keeper fill.

## Bindings and deployment

Apply account migrations through `0010_managed_bots.sql` before enabling the service. Both Workers use the same `oraclebot-accounts` D1 database. The private Worker also needs the `CUSTOMER_EXECUTORS` SQLite Durable Object binding declared in its Wrangler configuration.

| Setting | Worker | Purpose |
| --- | --- | --- |
| `EXECUTOR_TOKEN` | Public and private | Matching random service bearer, 32–256 characters. |
| `EXECUTOR_VAULT_KEY` | Private only | Base64url encoding of exactly 32 random bytes for AES-256-GCM. |
| `EXECUTOR_VAULT_KEY_ID` | Private only | Key version, default `v1`. |
| `EXECUTOR_PREVIOUS_VAULT_KEYS` | Private only, optional | JSON object of prior key IDs and base64url keys for rotation. Keep old keys until ciphertext is rewrapped or deleted. |
| `COINBASE_EXECUTION_ENABLED` | Private | Exact `true` enables the Coinbase adapter. Committed default is `false`. |
| `USER_TRADE_EXECUTOR` | Public | Service binding to this private Worker. |
| `LIVE_EXECUTION_ENABLED` | Public | Exact `true` enables new trade preparation/submission. |
| `EXECUTOR_AVAILABLE_VENUES` | Public | JSON allowlist; use `["coinbase"]` until another venue qualifies. |
| `EXECUTOR_RECONCILIATION_ENABLED` | Public | Exact `true` enables venue settlement reads in trade status. |

The service has no public `workers.dev` or preview URL. Every gateway request requires the service bearer, and requests carrying `Origin` are refused. Do not expose its Durable Object namespace to another untrusted Worker.

`GET /health` reports configuration readiness separately from each venue's implementation and enablement. It validates the current vault key's encoding and length. Readiness does not prove a live customer connection, subscription entitlement, deployed code identity or venue acceptance.

## Connection contract

All routes below are private `POST` endpoints except health. Responses contain public connection metadata only. The authenticated public Worker must construct `userId` and `wallet`; it must never accept those fields from an unauthenticated browser.

| Route | Exact outer request fields |
| --- | --- |
| `/v1/connections` | `{userId,wallet,input}` |
| `/v1/connections/list` | `{userId,wallet,cursor?}` |
| `/v1/connections/revoke` | `{userId,wallet,id}` |
| `/v1/connections/revoke-all` | `{userId,wallet}` |

Connection input is `{venue:"coinbase",apiKeyName,privateKey,portfolioId?,idempotencyKey}`. The key must be Coinbase ECDSA P-256. Both exported PKCS8 and SEC1 PEM formats are supported; Ed25519 credentials refuse. The authenticated Coinbase permissions response must prove `can_view=true`, `can_trade=true`, `can_transfer=false`, and a specific retail portfolio. An INTX portfolio refuses. A supplied portfolio must exactly match the provider's portfolio. Accounts from another portfolio or an incomplete account census refuse.

Credentials use randomized AES-GCM encryption with associated data binding account, wallet, connection, venue and format version. Only the encrypted envelope resides in Durable Object storage. D1 stores a credential-name fingerprint, portfolio and public connection metadata. Secret values must never be rendered in the DOM, logs or responses.

One active Coinbase connection is allowed per account, and an active credential cannot be shared between accounts. At most 16 active or unresolved encrypted authorities can remain in private storage. A rolling eight-attempt/24-hour limit bounds connection imports, including failures. Revoked credentials with no unresolved order are erased; public financial/audit history remains in D1 without a lifetime rotation limit. Idempotency hashes remain with that history. The list always includes all active/unresolved authority metadata first, followed by up to 25 historical rows and an opaque `nextCursor` or `null`. Pass the cursor unchanged for the next history page; active/unresolved rows repeat on every page and should be deduplicated by ID in the UI. A revoked connection cannot authorize new risk. Its encrypted credential is retained only while an already admitted order needs read-only reconciliation.

Account deletion must call `revoke-all` first. Delete the public account only after `{revoked:true,credentialsDeleted:true,pendingReconciliation:false}`. If an admitted order remains unresolved, the response has `credentialsDeleted:false,pendingReconciliation:true`; finish read-only reconciliation before deletion. Once no admitted order remains, cleanup erases all private ciphertext and journals and verifies that no credential envelope remains. The operation is idempotent and never closes or changes a financial position.

Before beginning that cleanup, the public account lifecycle sets a persistent deletion fence and marks execution initialization before its first credential import. The private gateway and final connection/trade admissions independently refuse a fenced account. An import already awaiting a provider response rechecks the fence before sealing and again in its final D1 insert; a raced failed insert removes its newly sealed envelope. Status, reconciliation and credential revocation remain usable while deletion is fenced.

## Trade and recovery invariants

The public trade boundary reserves a fee-inclusive quote-time USD notional under a signed, expiring wallet policy. Legacy five-field policies authorize spot at 1x only. Perpetual products and a maximum leverage require explicit version-2 consent. Existing policy bytes and hashes are never widened or rewritten.

Before planning, the service reconciles the customer portfolio's orders and refuses any nonterminal order or another unresolved Oraclebot intent. It pins Coinbase's HTTPS origin and supported USD spot products. The price comes from a fresh best bid/ask snapshot, sizing respects product increments and minimums, fees come from the customer's current taker tier and venue preview, and the order uses a price-bounded `sor_limit_ioc` configuration. There is no invented price, size or fee fallback.

Before sending, the service rechecks permissions, orders, fee tier, an exact fresh preview and portfolio-bound available balances. It signs the HTTP request, writes a durable journal, then performs one atomic D1 admission that rechecks the current user, grant, scope, policy and payload hashes, quote, connection, subscription and cumulative budget. A single provider send follows that admission. No later API retry can blindly repeat an admitted or uncertain order; the intent UUID is the provider client-order ID.

`reduceOnly:true` is accepted only for a Coinbase spot sell at 1x. The exact quoted base quantity must be owned and available both during preparation and again before sending. This narrowly permits reduced inventory after subscription loss. It does not bypass policy expiry, scope, revocation, asset restrictions, notional limits, unresolved-order reconciliation or connection revocation. It cannot borrow or open a short. Other unpaid trades refuse. Absent/false `reduceOnly` is omitted from canonical payloads to preserve earlier idempotency hashes.

An optional positive decimal-string `maxBaseQuantity` cap is accepted only on that explicit reduced Coinbase spot sell. The native order quantity is the lower of the budget-sized quantity and this cap, floored to the product increment. The cap is part of the canonical payload hash, and exact provider quantities never exceed it. It limits an automated bot to its recorded allocation even when the same portfolio holds additional manual or other-bot inventory. It supplies no price or fee and does not widen the notional budget. Absent caps leave earlier payload hashes unchanged.

`/v1/trades/reconcile` accepts exactly `{intentId,userId,wallet,resource,policyHash,payloadHash}`. Reconciliation remains available for an admitted intent after subscription or grant loss and with a revoked connection. It can read a historical order or perform a complete bounded client-order census. Failure to find an order does not prove it was never sent. Unknown outcomes retain their entire reservation.

Filled orders and partial fills conservatively consume the full reserved maximum, or the exact observed fill value plus fees when that exceeds the reservation. That settled consumption never becomes reusable policy budget. A canceled/failed order with no fill and no fees consumes zero only after authoritative reconciliation or a durable proof that no send could have occurred. Fresh receipt timestamps do not rewrite authoritative fill timestamps.

`reconcileCustomerTrade` in the public trade module supports cookie-authenticated account recovery without a current MCP grant. It is a status operation and cannot sign or submit a trade. Automated bot activation must separately bind a bot definition and trusted strategy signal to a customer-signed grant; a paper bot definition alone supplies no authority.

## Managed bot driver

`managed-bot-driver.js` provides the private Coinbase spot 0/1 exposure driver and an adapter to the same shared trade boundary. Root activation, OAuth consent, D1 repository and scheduler integration must supply its documented callbacks; the module alone does not activate a paper bot or schedule execution.

The driver recomputes immutable configuration, customer/client/grant/connection and closed-bar signal hashes. It accepts only a dedicated `managed-bot` client. The trusted source must supply a fresh closed-bar strategy signal with desired exposure exactly 0 or 1. A flat bot can buy; an allocated bot can sell only under its exact fill-ledger cap. Existing exposure is not topped up. An unresolved order holds all further actions. Grant expiry or revocation stops all new actions, including exits; subscription loss alone can permit the separately verified reduced-inventory path.

The injected repository must atomically serialize all signals for a bot, compare the exact loaded allocation and pending intent during claim, bind the prepared intent before submit, and apply each authoritative settlement at most once while comparing allocation-before. A per-signal lock alone is insufficient. Pause/configuration changes must revoke the dedicated grant atomically, or add an equivalent final signer admission fence; the driver's fresh read alone cannot close a later pause race. The source comments above `runManagedBot` specify the complete callback ABI. The hash helpers define canonical bytes for root integration.

The private signer independently identifies current managed grants from D1. Before a managed sale, it sums every allocation for that customer, wallet, connection and asset using exact decimal arithmetic, including paused bots. Fresh available inventory must cover that entire sum. Another bot's pending intent holds execution even when its venue order has already filled but its ledger remains unapplied. The service rechecks the managed rows after provider validation, then its final atomic signer admission compares the ordered complete critical row snapshot. A pause, allocation change, rebind or new pending fill invalidates admission. The sold quantity must also remain within the current bot's own ledger cap. Explicit customer manual grants retain their separately approved trade behavior.

That same final admission checks the current subscription's bot-slot capacity before a managed buy: three configured bots for Starter, ten for Advanced and no plan count limit for Unlimited. A downgrade after preview blocks new exposure when configured slots exceed the new allowance. The customer must pause excess definitions before managed buying resumes. A verified protective sale retains its separate reduced-inventory exception and still requires current wallet authority and all inventory/policy checks.

## Verification

The repository tests exercise actual loopback HTTP, method/path-bound ES256 verification, D1 migrations, encrypted storage and edge-to-private execution. They use generated fixture credentials and portfolios. They do not send orders to Coinbase or the Solana network.

Run the website's Node API suite from the repository root with `INDEX_NO_AUTO=1 node --test website/test/*.test.js`. Build this service with `wrangler deploy --dry-run --config website/execution/wrangler.jsonc`. Live acceptance additionally requires the deployed revision, real customer connection, provider preview/reconciliation and an explicitly coordinated financial acceptance test; never infer those from a successful build.
