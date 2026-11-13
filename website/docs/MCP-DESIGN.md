# Authenticated Oraclebot MCP design

Version: 0.1.1
Delta: v0.1.0 to v0.1.1; implement OAuth/MCP/intent ledgers and exact execution qualification limits.

The owner explicitly chose preauthorized sessions. There is no per-trade wallet prompt requirement. Login proves wallet ownership; a separate, explicit consent grants an agent read access or a finite trading policy. OAuth authorization never supplies a blockchain signature or replaces a customer venue connection.

## Identity and OAuth

Use `/mcp` as the canonical protected resource, with RFC9728 protected-resource discovery and OAuth authorization-server metadata. Start with the explicitly tested MCP2025-11-25 stateless Streamable HTTP profile. Support public-client authorization-code PKCE S256, exact registered redirects, single-use codes, exact client/resource/scope binding, short-lived hashed bearer credentials, rotating refresh credentials and immediate grant revocation. Do not forward MCP credentials to another service.

Scopes are `status:read`, `trade:prepare`, and `trade:submit`. Default consent is read access. Trading scopes require a separate wallet-backed consent binding the client, wallet, policy digest, nonce and expiry. Policies contain `venues`, `assets`, `maxTradeUsd`, `maxTotalUsd`, and `expiresAt`; all are finite and validated. No trading policy is silently inferred from login or subscription.

## Tools and execution boundary

`oraclebot_get_status` returns the token user wallet, own bot/status records, usage and truthful execution/delegation readiness. `oraclebot_request_trade` prepares an owned, expiring, idempotent intent. `oraclebot_get_trade_status` reads only that owner intent. `oraclebot_submit_trade` submits only a verified, unchanged intent within the live grant and policy. Tool schemas reject wallet/user/account/signer overrides.

Every execution call derives the principal from a valid resource-bound bearer token. It checks current entitlement, grant revocation, expiry, per-trade/cumulative reservations, selected venue/asset, fresh quote and the customer-owned signing/venue authority. Reserve limits atomically before a venue call. Ambiguous submits remain unknown and are never automatically retried. A missing supported executor or signer refuses before a claimed order success. Nothing loads an owner-machine key. The same principal and economic gates apply regardless of which agent calls.

The current hosted site has inert paper definitions and analysis only. Customer Coinbase/Jupiter connection and signing adapters remain separate implementation requirements. Do not mislabel an intent as an executed trade. Preauthorized sessions can execute without repeated prompts only when the connected wallet/venue supports the actual delegated authority.

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

The user requested preauthorization. Browser consent signs once per finite grant; trade request/submit calls do not ask for individual approval. Settings revocation is immediate. Successful execution module fixtures use an explicitly mocked private service binding. No customer Coinbase credential store, Solana delegated signing authority, venue reconciliation worker or live order was created. The default deployment keeps LIVE_EXECUTION_ENABLED=false and has no USER_TRADE_EXECUTOR binding.

A future adapter must enforce customer authority and the signed policy itself. It must reconcile the venue before preparing an order and never retry an ambiguous submit. Its prepare response binds intentId, wallet, payloadHash, policyHash, verified customer connection and delegation, and an explicit fee-inclusive quote with quotedAt and expiresAt. Its submit acknowledgement binds the same intent, quote and delegation. submitted does not mean filled. The public output reports filled:null until authoritative reconciliation exists. Unknown/submitting/submitted reservations never age out in generic cleanup. Account deletion cannot erase those records.
