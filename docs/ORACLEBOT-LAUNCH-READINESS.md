# Oraclebot launch readiness

Version: 0.1.2
Delta: Record the three chosen plans, verified test portal, local dashboard repair and wallet-bound preauthorization requirement.
Verified: 2026-11-13. This is a deployment snapshot and implementation plan.

## Why the free trial did not start

The latest public health read still reports website `0.1.0`, storage configured,
and billing, analysis engine and live execution unavailable. A connected Stripe
assistant does not provision credentials in the deployed Worker. Binding flags
also do not prove a database operation, engine job or subscription lifecycle.

The owner has now chosen all three USD monthly plans. Do not ask for pricing
again:

| Plan | Monthly renewal | Bot limit | Backtests per UTC day |
| --- | ---: | ---: | ---: |
| Starter | $9.99 | 3 | 10 |
| Advanced | $29.99 | 10 active slots | Unlimited |
| Unlimited | $49.99 | Unlimited | Unlimited |

The first eligible subscription receives seven free days. Configured paper
records reserve slots; paused and archived records release them. The pending
website `0.2.0` implementation enforces these policies atomically, keeps one
backtest in flight per account, and keeps Checkout explicitly disabled until the
promised hosted service qualifies. Unlimited counts do not remove resource or
risk limits. Creating a paper definition does not start an execution worker.

Dedicated local credentials can read the owner's exact three existing Prices
and portal, all in **test mode**. The supplied account number differs from the
key's account response; Connect scoping was refused. Access to those exact test
objects is verified, but live merchant ownership is not inferred from it. Test
account readiness flags do not establish live activation or KYC status.

The exact test portal now allows the three plans, preserves the remaining trial,
disables quantity changes, invoices prorated upgrades and schedules lower-price
downgrades at period end. Cancellation and payment updates were preserved. No
customer, subscription, invoice or charge was created by this configuration.
Its test identifiers and credentials are not production billing configuration.

## Current capability boundaries

| Capability | Implemented | Still required |
| --- | --- | --- |
| Website and research journal | Initial Cloudflare Worker, responsive workspace and deterministic public research archive | Deliver the audited and tier releases; expand articles editorially with their evidence |
| Accounts | Solana wallet challenge, signature verification, hashed server session and tenant D1 records | Verify the final deployed wallet, isolation and cleanup round trip |
| Membership | Seven-day trial, three plan policies, atomic usage limits, canonical signed webhook handling and configured portal | Matching live merchant credentials/objects, webhook delivery and complete billing lifecycle acceptance |
| Backtests | Read-only CPython adapter, canonical exposure strategies and cached bars with costs/provenance | Hosted runtime, maintained public data, durable jobs/resource limits and remaining local runner parity |
| Hosted Oracle | Read-only per-coin archive adapter, eligibility ranking and freshness refusal | Dedicated feed/Oracle writers, durable archives, restart ownership and actual fresh hosted acceptance |
| Coinbase bots | Tenant-owned inert paper definitions | Customer-specific venue connection, execution, risk enforcement, reconciliation and recovery |
| Jupiter leveraged positions | Configuration surface | Supported perpetual-position integration, the customer's actual delegated signing authority and verified economics |
| Agent MCP | Wallet-bound OAuth and bounded preauthorization are commissioned separately | Protocol/authentication implementation, tenant isolation, revocation and the same verified customer execution path |

Local control-room release `0.4.9` is separately delivered and installed. It now
selects the sole research bot, shows its actual independent trial capital and
pending settlement, and explains Oracle eligibility. The active local pipeline
remains on its original `0.4.8` bundle and cohort. This local repair does not
connect the public hosted engine.

The current adapter takes strategy defaults and the latest bounded contiguous
cached bars. It is not the complete local grid, DCA, pair, event or experiment
configuration surface. Full parity needs an operation/strategy inventory,
identical input/cost conventions and shared known-answer checks. Those are code
requirements, not requests for the owner to provide code or run setup commands.

## Cloudflare hosting

The existing Worker can host the website, HTTP API, authentication, Stripe calls
and D1 account records. Workers can make HTTPS calls to Coinbase, Jupiter and
Stripe using the appropriate customer or service authority.

The canonical engines use CPython, NumPy and pandas. Cloudflare Containers can
host that runtime and require Workers Paid. An ordinary Worker request does not
provide a persistent Python trading process. Containers need explicit lifecycle
and activity handling, and their disks are ephemeral. Persist jobs, ownership
and archives outside process memory/container disk, with durable storage such
as D1/R2 and a tested snapshot/restore design. A warm container is not proof of
an uninterrupted bot or a recovered SQLite archive.

The current Wrangler configuration has assets, D1, routes and cleanup cron. It
does not yet configure Containers, Durable Objects, Queues or R2 for this engine.
The repository Docker image starts the read-only adapter; it does not start a
feed, recorder, Oracle writer or historical acquisition service.

Keep analysis and execution separate. The Worker checks tenant and entitlement;
bounded jobs use versioned public data; customer execution uses only that
customer's authority and risk policy. Persist receipts and reconcile with the
venue before planning. Never automatically retry an ambiguous order submission.
The owner's local control room, keys and paper cohorts stay outside this hosted
customer boundary.

## Inputs needed from the owner

Pricing and the intended test portal are resolved. The remaining Stripe input
is a dedicated **live secret key for the intended merchant**, once that account
is activated. Keep it in private local configuration; do not paste it into chat.
The agent can create matching live Products, Prices, portal configuration and
webhook, then provision Worker secrets and verify them. The owner need not
manually recreate the three plans or supply a webhook secret in advance.

A card collected at signup, seven free days for an eligible first subscription,
then the disclosed renewal and self-service cancellation remain the billing
contract. The hosted features must work before starting a customer's trial.

The owner explicitly corrected an accidental per-trade approval selection:
**use preauthorized agent sessions**. Initial consent binds the actual wallet,
agent, allowed venues/assets, finite per-trade and cumulative limits, expiry and
revocation. No prompt is required for every trade inside that authorization.
Login-only signatures and MCP OAuth tokens do not themselves supply blockchain
signing authority. The customer's connected venue or wallet must support the
actual delegation, and the execution service must enforce the same limits.
Never substitute the operator's wallet or permit a model-supplied wallet override.

The remaining engine, parity, customer connections, signing, MCP and lifecycle
work belongs to implementation. Request an owner-only platform login or service
permission only when a concrete provisioning step actually requires it.

## Target hosted billing bindings for website 0.2.0

| Binding | Meaning |
| --- | --- |
| `DB`, `ASSETS` | Existing D1 account database and public assets |
| `APP_ORIGIN` | Canonical HTTPS wallet challenge origin |
| `APP_VERSION`, `RELEASE` | Deployed source identity |
| `BILLING_LAUNCH_ENABLED` | Exact `true` opens new Checkout; default is `false` |
| `STRIPE_STARTER_PRICE_ID` | Allowlisted Starter recurring Price |
| `STRIPE_ADVANCED_PRICE_ID` | Allowlisted Advanced recurring Price |
| `STRIPE_UNLIMITED_PRICE_ID` | Allowlisted Unlimited recurring Price |
| `STRIPE_PORTAL_CONFIGURATION_ID` | Explicit matching customer portal |
| `STRIPE_SECRET_KEY` | Private credential for the same Stripe account/mode |
| `STRIPE_WEBHOOK_SECRET` | Secret for this site's exact webhook endpoint |
| `ENGINE_URL`, `ENGINE_TOKEN` | Authenticated hosted analysis service |

Configure Checkout and subscription lifecycle events at:

https://oraclebot.io/api/billing/webhook

The webhook verifies the raw-body signature, reconciles canonical Stripe state,
serializes nonterminal plan updates and preserves terminal cancellation. A
success redirect does not grant access. Existing customers retain portal access
while new Checkout is disabled.

## Acceptance before paid activation

Verify final deployed wallet login, tenant isolation and own-account cleanup;
seven-day test Checkout; actual signed webhooks/replay; trial expiry, plan changes
and cancellation; and portal behavior. Verify hosted backtests and fresh per-coin
Oracle results against canonical engines, including the local parity matrix.
Inspect deployed source/version bindings separately from source tests.

For the chosen coin and horizon, put the highest-ranked eligible current strategy
at the top with its direction, evidence, rank and expiry. If none qualifies,
explain the missing evidence. A separately labelled unqualified shadow direction
must not replace a qualified aggregate or imply profit probability. Do not invent
a winner or reuse an expired forecast to fill the card.

Verify each customer execution integration with scoped authority, deterministic
risk refusals, budget concurrency, revocation, restart recovery and ambiguous-
submit handling. A mock executor or a local paper result does not establish a
hosted order. Keep paid Checkout and live execution unavailable until their
respective acceptance gates pass.

## References

https://oraclebot.io/api/health

https://developers.cloudflare.com/containers/get-started/

https://developers.cloudflare.com/containers/faq/

https://developers.cloudflare.com/containers/api/durable-object-container/

https://docs.stripe.com/billing/subscriptions/trials/free-trials

https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
