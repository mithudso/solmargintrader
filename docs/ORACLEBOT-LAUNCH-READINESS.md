# Oraclebot launch readiness

Version: 0.1.0
Delta: initial source and production capability inventory; separates owner decisions from engineering work.
Verified: 2026-11-12. This document is a deployment snapshot, not a promise of live trading availability.

## Why the free trial did not start

The production health endpoint currently reports website version `0.1.0`,
`storage: true`, `billing: false`, `engine: false` and `liveExecution: false`.
These capability flags describe configured bindings. They do not establish a
successful database operation, engine job or Stripe subscription lifecycle.
The Stripe connection in the assistant is working. That connection does not
install Stripe credentials or a recurring subscription Price in the deployed
Cloudflare Worker.

The server requires `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID` and
`STRIPE_WEBHOOK_SECRET` before it creates Checkout sessions. An eligible first
subscription receives `subscription_data[trial_period_days]=7`. The present
failure occurs before that trial can be created.

The pending website `0.1.1` change disables the trial call to action when billing
is unavailable and explains the unavailable state. Source tests passing do not
mean that this version has been deployed or that a real trial has succeeded.

## What exists and what still needs implementation

| Capability | Current state | Required for the requested service |
| --- | --- | --- |
| Public website and responsive workspace | Deployed initial release | Deploy and verify the audited release |
| Accounts and authentication | Solana wallet challenge, signature verification, server session and tenant account storage implemented | Verify a real deployed wallet round trip; decide any later email recovery feature separately |
| Persistent account data | Cloudflare D1 stores users, sessions, paper definitions and billing records | Exercise tenant isolation and account lifecycle in the deployed environment |
| Seven-day subscription trial | Checkout, signed webhook entitlement and customer portal code implemented; production billing unavailable | Choose merchant and renewal price, provision secrets, configure webhook and portal, then verify test-mode lifecycle before live activation |
| Backtests | Read-only Python adapter exists | Host the Python runtime, public-market cache and bounded job queue; complete the remaining local-runner parity matrix |
| Per-coin Oracle | Evidence-aware UI and adapter exist | Host fresh public-market inputs and the read-only Oracle archive; maintain eligible strategy ranking and freshness |
| Coinbase bot creation | Tenant-owned inactive paper definitions exist | Implement customer venue authorization, isolated execution workers, risk checks, reconciliation and actual acceptance |
| Jupiter leveraged positions | Configuration surface exists; no hosted customer execution | Implement the current supported perpetual-position integration and customer-specific authorization/signing lifecycle |
| Research blog | Deterministic public research archive exists | Expand individual articles editorially; preserve their original evidence and limitations |

The adapter currently exposes a bounded strategy subset. It is not the complete
local grid, DCA, pair and event runner surface. Full parity needs an explicit
operation/strategy inventory, identical input and cost conventions, and shared
known-answer checks. Infrastructure credentials alone cannot finish this work.

## Cloudflare can host the service

Use the existing Worker for static assets, HTTP API, wallet authentication,
Stripe calls and account storage. Workers can make HTTPS requests to Coinbase,
Jupiter and Stripe, subject to each provider's own authentication and limits.
Use D1 for application records and durable job coordination for queued analysis
and execution work.

The canonical engines use CPython with NumPy and pandas. Run them in Cloudflare
Containers or another container service, with an authenticated internal API,
bounded resources and public-market data storage. An ordinary Worker request
does not provide a persistent Python trading process. Workers' request CPU and
post-response lifetime limits must not become the scheduler for a trading bot.

Containers also require an explicit lifecycle. Persist job ownership and progress
outside process memory, renew required activity, detect restarts, reconcile with
the venue before planning, and refuse ambiguous submissions. A container being
available does not prove that an uninterrupted execution service exists.

The recommended deployment boundary is:

1. The browser authenticates with a wallet and calls the Worker.
2. The Worker checks the account, subscription, tenant ownership and operation.
3. A bounded job service runs canonical analysis against versioned public data.
4. A separate customer execution worker uses only that customer's explicit venue
   authority and risk policy. Analysis does not acquire trading authority.
5. Durable receipts drive account status, reconciliation and audit history.

Keep the owner's local control room, wallet keys and existing paper cohorts
outside this hosted tenant boundary. A wallet login signature authorizes a
session; it does not authorize spending or orders. A Jupiter Swap quote does not
establish a leveraged perpetual position.

## The decisions needed from the owner

**Choose the Stripe merchant account and the renewal amount and interval.** No
Oraclebot merchant or recurring Price has been selected. The connected-account
inventory remains private. Do not infer the correct merchant from another
site's name or copy its existing Price.

The working billing default is a card collected at signup, seven free days for
an eligible first subscription, then the disclosed recurring charge, with
self-service cancellation. The code already asks for a payment method by
Stripe's default subscription behavior. No amount has been selected. Cardless
trials would require an explicit missing-payment-method policy and additional
lifecycle tests.

After the merchant and price are fixed, credentials must be provisioned through
private platform configuration. Do not paste API keys or webhook secrets into
chat. The assistant's Stripe connector and the deployed Worker's secret store
are separate authorization surfaces. Complete any platform login only when an
actual deployment step requires it.

The remaining hosted engine, strategy parity, customer execution and lifecycle
work belongs to implementation. These are not requests for the owner to supply
code or run ordinary setup commands.

## Exact hosted bindings

| Binding | Meaning |
| --- | --- |
| `DB` | Existing account D1 binding |
| `ASSETS` | Public site assets |
| `APP_ORIGIN` | `https://oraclebot.io`, the wallet challenge origin |
| `APP_VERSION` / `RELEASE` | Deployed source release identifiers |
| `STRIPE_PRICE_ID` | Chosen recurring Price in the chosen Stripe account |
| `PRICE_LABEL` | The same disclosed renewal amount and interval |
| `STRIPE_SECRET_KEY` | Private server credential for that Stripe account |
| `STRIPE_WEBHOOK_SECRET` | Secret for this site's exact webhook endpoint |
| `ENGINE_URL` | Provisioned authenticated analysis service |
| `ENGINE_TOKEN` | Private Worker-to-engine credential |

Configure Checkout and subscription lifecycle events at:

https://oraclebot.io/api/billing/webhook

The webhook verifies the raw-body signature and fetches the canonical
subscription before granting access. A success redirect never grants entitlement.
The customer portal needs cancellation and payment-method management enabled.

## Oracle behavior required for launch

For the selected coin and horizon, put the highest-ranked eligible strategy at
the top. Show its current direction, evidence date, forecast expiry, cost-aware
out-of-sample results and reasons for its rank. Keep the forecast distinct from
an order instruction. Show a neutral direction when that is the strategy's
actual signal.

If no strategy has eligible fresh evidence, show a clear unavailable state and
the missing requirement. Do not invent a winner, reuse expired forecasts or
guarantee a direction merely to fill the top card. A profitable historical
backtest does not establish predictive reliability.

## Acceptance before enabling a paid service

Verify a deployed wallet login and tenant isolation; a seven-day test-mode
Checkout; signed webhook delivery, replay handling, cancellation and trial
expiry; and correct portal behavior. Verify authenticated hosted backtests and
fresh per-coin Oracle ranking against the canonical engines. Inspect the loaded
release and actual capability flags after deployment.

Verify each execution integration separately with customer-scoped test
authority, deterministic risk refusals, restart recovery, reconciliation and
ambiguous-submit handling. Keep live execution unavailable until those checks
pass. Existing source tests and local paper results do not establish hosted
orders or subscription settlement.

## References

https://oraclebot.io/api/health

https://developers.cloudflare.com/workers/platform/limits/

https://developers.cloudflare.com/containers/api/durable-object-container/

https://docs.stripe.com/billing/subscriptions/trials/free-trials

The repository's website README documents the current build, migration,
deployment and rollback commands. The full repository audit report records
source checks and their remaining limits separately from this launch plan.
