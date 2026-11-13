# Oraclebot launch readiness

Version: 0.1.4
Delta: Verify the dedicated live merchant and provisioned billing bindings; retain closed launch gates and explicit provider lifecycle gaps.
Updated: 2026-11-13. Source verification and recorded deployment observations are separate below.

## Why the free trial did not start

The deployed website is `0.3.0`. Accounts and storage are configured. New
Checkout remains deliberately disabled because the hosted analysis engine and
customer execution service are unfinished. The new live Stripe key resolves the
billing credential gap; it does not start a trial or qualify those services.

The owner has now chosen all three USD monthly plans. Do not ask for pricing
again:

| Plan | Monthly renewal | Bot limit | Backtests per UTC day |
| --- | ---: | ---: | ---: |
| Starter | $9.99 | 3 | 10 |
| Advanced | $29.99 | 10 active slots | Unlimited |
| Unlimited | $49.99 | Unlimited | Unlimited |

The first eligible subscription receives seven free days. Configured paper
records reserve slots; paused and archived records release them. The deployed
website `0.3.0` implementation enforces these policies atomically, keeps one
backtest in flight per account, and keeps Checkout explicitly disabled until the
promised hosted service qualifies. Unlimited counts do not remove resource or
risk limits. Creating a paper definition does not start an execution worker.

On 2026-11-13 a private Stripe account read verified the replacement dedicated
**live** secret key against the merchant registered to `https://oraclebot.io`.
Card payments, charges and payouts are enabled; Stripe reports no currently due
requirements. The original three live USD monthly Prices were reused. The
publishable key is not required by this server-side Checkout redirect flow.

A dedicated live portal and four-event webhook were created. All six billing
bindings were provisioned together through Wrangler: three Price IDs, the portal
configuration, secret key and webhook signing secret. Provider IDs and credentials
remain in private operational configuration; no real customer, subscription,
invoice or charge was created by this setup.

The live portal permits price-only changes, preserves the remaining trial,
requests immediately invoiced prorations and period-end lower-price changes,
and enables period-end cancellation, payment updates and invoice history.
These are accepted configuration values, not demonstrated subscription outcomes.
Stripe's guide restricts scheduled downgrades to the same product, while the API
rejects duplicate monthly intervals within one product's portal price list.
The original three-product catalog was preserved. Only the unused candidate
product and its three Prices created during this setup were archived. Verify
actual cross-product plan-change timing in test mode before paid activation;
implement a server-owned schedule if the portal cannot honor the policy.

The live webhook is pinned to API version `2026-10-28.endive` and receives only
`checkout.session.completed` and `customer.subscription.created`, `.updated`
and `.deleted`. Independent acceptance passed73bounded checks, including correct/incorrect
webhook signing-secret refusals using missing-id payloads that stop before
database operations. These checks do not prove a delivery from
Stripe or a complete trial, renewal, upgrade, downgrade or cancellation lifecycle.

The billing-only Cloudflare version is
`07171eac-6e7b-4424-875b-140f80fe2d59`; its source remains website `0.3.0`.
Both launch flags remain `false`. Independent acceptance and sanitized setup
receipts are recorded separately under:

/Users/mitch/.local/state/oraclebot-live-billing-20261113/

## Current capability boundaries

| Capability | Implemented | Still required |
| --- | --- | --- |
| Website and research journal | Delivered Cloudflare Worker0.3.0, responsive workspace and deterministic public research archive | Evidence-backed article expansion |
| Accounts | Solana wallet challenge, signature verification, hashed server session, tenant D1 records and fenced browser account transitions | Real customer wallet-extension acceptance; synthetic hosted isolation/cleanup already passed |
| Membership | Seven-day trial, three plan policies, atomic usage limits, canonical signed webhook handling and configured portal | Actual webhook delivery, complete test billing lifecycle and plan-change timing acceptance |
| Backtests | Read-only CPython adapter, canonical exposure strategies and cached bars with costs/provenance | Hosted runtime, maintained public data, durable jobs/resource limits and remaining local runner parity |
| Hosted Oracle | Read-only per-coin archive adapter, eligibility ranking and freshness refusal | Dedicated feed/Oracle writers, durable archives, restart ownership and actual fresh hosted acceptance |
| Coinbase bots | Tenant-owned inert paper definitions | Customer-specific venue connection, execution, risk enforcement, reconciliation and recovery |
| Jupiter leveraged positions | Configuration surface | Supported perpetual-position integration, the customer's actual delegated signing authority and verified economics |
| Agent MCP | Wallet-bound OAuth PKCE S256, scoped MCP status and trade intents, separately signed finite preauthorization, atomic budget reservations and immediate grant revocation | Actual customer execution/delegation path; synthetic deployed authentication/isolation already passed |

The combined local control-room environment ecosystem `0.4.12`, Oracle `0.2.4`
and observer `1.2.1` completed independent installed acceptance with twenty
passing gates. Earlier `0.4.9` and `0.4.11` evidence remains historical. The active
local pipeline retains its original `0.4.8` bundle and cohort. Local control-room
and forecast improvements do not connect the public hosted engine.

This follow-up also repairs a required-CI frozen SQLite reader recovery case in
manager source `0.7.4`; ecosystem source `0.4.13` pins that manager version.
The accepted installed `0.4.12` owner prefix was not modified or restarted.
Source regression/CI checks are separate from a future owner runtime promotion.

The combined website source passes129Node cases,28actualChrome groups,
JavaScript quality, syntax and Worker dry-run checks. Successful executor
fixtures use mocks. These checks do not establish deployed authentication,
delegated signing, a venue order or a filled position. Both Wrangler launch flags
remain `false`, and no `USER_TRADE_EXECUTOR` service binding is provisioned.
The wider audit retains its recorded M3/M5/T4 qualifications; it does not claim
repository convergence.

Actual final CI, merge, installation, Cloudflare deployment and hosted acceptance
belong in the external delivery receipt:

/Users/mitch/.local/state/oraclebot-final-delivery-20261113/delivery.json

An absent or incomplete receipt does not establish any of those outcomes.

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

Pricing, the intended live merchant and the dedicated live key are resolved.
The three existing live Prices, new live portal and webhook are configured in
the Worker. No additional Stripe credential is required for this implementation.
Keep credentials in private local configuration; do not paste them into chat.
Actual provider delivery and billing lifecycle acceptance remain engineering
work before activation, together with the unfinished hosted services.

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

The remaining engine, parity, customer connections, delegated signing and
provider lifecycle work belongs to implementation. Request an owner-only platform login or service
permission only when a concrete provisioning step actually requires it.

## Hosted billing and execution bindings for website 0.3.0

| Binding | Meaning |
| --- | --- |
| `DB`, `ASSETS` | Existing D1 account database and public assets |
| `APP_ORIGIN` | Canonical HTTPS wallet challenge origin |
| `APP_VERSION`, `RELEASE` | Deployed source identity |
| `BILLING_LAUNCH_ENABLED` | Exact `true` opens new Checkout; default is `false` |
| `LIVE_EXECUTION_ENABLED` | Exact `true` permits qualified execution; default is `false` |
| `STRIPE_STARTER_PRICE_ID` | Allowlisted Starter recurring Price |
| `STRIPE_ADVANCED_PRICE_ID` | Allowlisted Advanced recurring Price |
| `STRIPE_UNLIMITED_PRICE_ID` | Allowlisted Unlimited recurring Price |
| `STRIPE_PORTAL_CONFIGURATION_ID` | Explicit matching customer portal |
| `STRIPE_SECRET_KEY` | Private credential for the same Stripe account/mode |
| `STRIPE_WEBHOOK_SECRET` | Secret for this site's exact webhook endpoint |
| `ENGINE_URL`, `ENGINE_TOKEN` | Authenticated hosted analysis service |
| `USER_TRADE_EXECUTOR` | Fixed private service binding for customer-owned venue/delegation verification and execution; currently absent |

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

For MCP, verify public-client registration, separately signed wallet policy,
PKCE exchange, resource/scope isolation, status, revocation and account cleanup
against the deployed Worker. Missing execution authority must refuse before any
trade reservation or claimed order success. A login signature or OAuth bearer
token cannot substitute for actual customer signing authority.

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
