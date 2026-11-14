# Authenticated Oraclebot MCP design

Version: 0.2.0
Delta: v0.1.2 to v0.2.0; add explicit product/leverage policy scope, customer executor and managed-bot isolation.

The owner explicitly chose preauthorized sessions. There is no per-trade wallet prompt requirement. Login proves wallet ownership; a separate, explicit consent grants an agent read access or a finite trading policy. OAuth authorization never supplies a blockchain signature or replaces a customer venue connection.

## Identity and OAuth

Use `/mcp` as the canonical protected resource, with RFC9728 protected-resource discovery and OAuth authorization-server metadata. Start with the explicitly tested MCP2025-11-25 stateless Streamable HTTP profile. Support public-client authorization-code PKCE S256, exact registered redirects, single-use codes, exact client/resource/scope binding, short-lived hashed bearer credentials, rotating refresh credentials and immediate grant revocation. Do not forward MCP credentials to another service.

Scopes are `status:read`, `trade:prepare`, and `trade:submit`. Default consent is read access. Trading scopes require a separate wallet-backed consent binding the client, wallet, policy digest, nonce and expiry. Legacy policies contain `venues`, `assets`, `maxTradeUsd`, `maxTotalUsd`, and `expiresAt`; they permit spot trades at 1x only. Version2 additionally binds `version:2`, `products`, and `maxLeverage` explicitly. USD limits are fee-inclusive notional, not collateral; all are finite and validated. No trading policy is silently inferred from login or subscription.

## Tools and execution boundary

`oraclebot_get_status` returns the token user wallet, own bot/status records, usage and truthful execution/delegation readiness. `oraclebot_request_trade` prepares an owned, expiring, idempotent intent. `oraclebot_get_trade_status` reads only that owner intent. `oraclebot_submit_trade` submits only a verified, unchanged intent within the live grant and policy. Tool schemas reject wallet/user/account/signer overrides.

Every execution call derives the principal from a valid resource-bound bearer token. It checks current entitlement, grant revocation, expiry, per-trade/cumulative reservations, selected venue/asset, fresh quote and the customer-owned signing/venue authority. Reserve limits atomically before a venue call. Ambiguous submits remain unknown and are never automatically retried. A missing supported executor or signer refuses before a claimed order success. Nothing loads an owner-machine key. The same principal and economic gates apply regardless of which agent calls.

Paper definitions remain inert until a dedicated managed-bot signature binds their exact configuration and customer connection. The private Coinbase executor implements isolated encrypted credentials, fresh previews, final policy admission, stable-order-id reconciliation and verified fills. Jupiter native delegation remains gated pending complete filled-position and cumulative-authority qualification. Do not mislabel an intent as an executed trade. Preauthorized sessions can execute without repeated prompts only when the connected wallet/venue supports the actual delegated authority.

## Required checks

Exercise two-wallet isolation, cookie-only refusal, token expiry/revocation/audience, OAuth redirect/client/resource/PKCE mismatch, concurrent code redemption, refresh replay, policy consent tampering, cumulative-limit concurrency, payload/idempotency mismatch, wrong signer/owner, missing executor and ambiguous-submit retention. Preserve existing billing/auth tests. Verify source and deployed behavior separately.

## Protocol references

https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

https://modelcontextprotocol.io/specification/2026-07-28/server/discover.md

https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http.md

The2026profile changes headers, metadata and discovery. It is not interchangeable with the2025 initialization profile.

## Implemented boundary

Website0.3.0 routes protocol requests before its single-page asset fallback. OAuth code/token credentials are hash-only. Separate wallet consent binds agent, principal, audience, scopes, policy digest, nonce and expiry. D1 immutable grant identity and atomic writes enforce revocation, cumulative reservations and known-plan entitlement. A meaningful NULL-plan webhook race failed before the canonical-plan SQL fences and passes afterward. The complete Worker fixture exercises actual synthetic Ed25519 login and policy signatures, PKCE exchange, two-wallet isolation, immediate revocation, missing-executor refusal, selective expiry and account-deletion races. These fixtures do not establish deployed or real-provider acceptance.

The user requested preauthorization. Browser consent signs once per finite grant; trade request/submit calls do not ask for individual approval. Settings revocation is immediate. The private Worker is service-bound and has no public routes. It rejects transfer-enabled Coinbase keys, enforces exact decimal fees/quotes and never loads an operator account. Its actual HTTP/SQLite provider fixtures establish tested contracts, not real customer order acceptance. `LIVE_EXECUTION_ENABLED=false` remains the deployment default.

Managed bots use dedicated internal clients and distinct signed grants. Consent includes bot/configuration/strategy revision, connection, policy and expiry. An external MCP grant cannot be reused. Atomic per-bot leases, durable pending intents and exactly-once fill settlement protect the ledger. Reduce-only sales carry a bot allocation cap; final private admission also protects aggregate allocations, pending fills, paused bots and plan capacity. Unknown submissions retain their commitments indefinitely until venue reconciliation. Account deletion must fence writers and verify private credential erasure before cascading records.

## Account transitions and diagnostics

The browser invalidates account work before login, logout or deletion begins. It applies private responses only while the captured identity, request and account generation remain current. It sends optional X-Oraclebot-Account with the captured identity; the Worker rejects a different cookie principal with409 account_changed. The header cannot choose a wallet or authorize access. An unavailable session remains unknown and offers retry. Confirmed expiry clears the former private view immediately.

USD amounts must be positive exact cents. Subcent and overprecision inputs fail before execution. Closed diagnostic vocabularies classify OAuth replay, MCP authentication outages, authorization refusal and execution failures. Events contain no credentials, wallet addresses, signatures, client URLs, request arguments or upstream bodies. A failed diagnostic sink cannot change authorization, execution or response semantics.
