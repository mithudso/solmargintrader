# Oraclebot authenticated agent access

Version: 0.1.0
Delta: Initial source qualification; hosted acceptance pending.

Website0.3.0 adds wallet-bound OAuth and MCP access above the three subscription tiers. The owner corrected an accidental selection and chose finite preauthorization. A separate wallet-signed message grants an agent selected venues/assets, per-trade and cumulative USD limits, expiry and immediate revocation. Subsequent request and submit calls do not ask for individual wallet approvals. Login alone cannot authorize trading.

The hosted endpoint is https://oraclebot.io/mcp . It uses explicit MCP2025-11-25 JSON POST and public-client authorization-code PKCE S256. Every request validates the resource-bound bearer principal; agent arguments cannot select a different wallet, account, signer or endpoint. Settings displays consent and agent revocation. Browser account transitions invalidate pending consent immediately.

The scoped independent security review resolved current-plan and active-grant-history races plus three browser consent boundaries. Full106Node cases, independent49boundary cases and17actualChrome groups passed with exit0. The reviewer independently repeated all17browsergroups. JavaScript quality, syntax, diff and Wrangler dry-run passed0. Exact source hashes and qualification limits are in ../.cdo/reviews-2026-11-13/website-mcp-independent.json . The audit of the earlier823semantic files remains bound to its own frozen commit; this delta does not relabel that audit CLEAN.

No customer live execution adapter is provisioned. A login or policy message cannot sign an on-chain transaction. Financial intents refuse without a verified customer connection, delegated authority, fresh explicit fee-inclusive quote and the fixed private executor binding. Success fixture paths use mocks. A submit acknowledgement never claims a fill. Ambiguous results retain budget and cannot automatically retry; account deletion cannot erase unresolved submissions.

Production deployment, additive migrations0003/0004/0005 and independent hosted wallet/MCP acceptance are pending. Public billing and execution remain off. The supplied Stripe credentials and existing three Prices/portal are test mode. A dedicated live merchant key is still required before live billing qualification. Hosted CPython analysis/parity, continuous public-market evidence and customer venue/signing implementations remain engineering work. These gaps cannot be solved by copying the owner's local keys or exposing the local control room.
