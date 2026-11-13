# oraclebot.io

Cloudflare-hosted wallet account and research workspace. This is a separate web
surface over the existing research tools. It never exposes the owner's control
room, trading accounts, wallet keys or signing services.

## What is implemented

- Responsive workspace, per-coin Oracle view, bot configuration, backtest form,
  research library, account and billing controls.
- Solana wallet authentication with a domain-bound, expiring, single-use signed
  message. Accounts and hashed server sessions live in Cloudflare D1. Connecting
  a wallet does not grant transaction or trading permission.
- Tenant-owned paper bot definitions. Stored definitions do not execute. The API
  rejects live mode. Pausing and archiving only affect the account's definitions.
- Stripe subscription Checkout with a seven-day trial on the first eligible
  subscription, signed webhooks, verified subscription entitlement and customer
  portal access. No checkout redirect grants access. The server controls prices.
- Public research archive with source provenance and original limitations.
- A separate read-only Python engine adapter reusing the canonical strategy,
  backtest and Oracle packages. Missing cached inputs or eligible Oracle evidence
  produce an unavailable state. There is no synthetic market-data fallback.

## Current deployment limits

The website can be deployed independently. Checkout stays disabled by default, including when test Prices are configured.
Opening it needs an explicit owner launch decision and the bindings below,
including a configured cancellation portal. Analysis needs a provisioned Python
engine with a public-market cache and a read-only Oracle archive. Live automated
Coinbase and Jupiter accounts need a separate implementation of per-user venue
authorization, isolated workers, risk enforcement, reconciliation and verified
signing. The website does not inherit the owner's existing trading authority.

Do not describe this release as a working paid live-trading service. The UI and
health API report these capabilities independently.

## Membership policies (website 0.2.0)

The Worker owns the policies and exposes them through `/api/config`. The browser
sends only `plan: starter`, `advanced` or `unlimited` to Checkout. It cannot choose
a Price, renewal amount, entitlement or quota. The seven-day trial applies only
to the first eligible subscription, across all three plans.

| Plan | Monthly renewal (USD) | Bot slots | Backtests/day (UTC) |
| --- | ---: | ---: | ---: |
| Starter | $9.99 | 3 | 10 |
| Advanced | $29.99 | 10 | Unlimited |
| Unlimited | $49.99 | Unlimited | Unlimited |

A `configured` paper definition reserves a bot slot. It does not execute or
represent a live/active venue bot. Paused and archived definitions free a slot.
The conditional D1 insert counts every status except `paused` and `archived`, so
an unknown stored status cannot bypass capacity. The existing pause/archive
allowlist stays unchanged; there is no activation or resume route. Any future
activation or resume must enforce the same atomic slot gate before changing a
record to a slot-reserving status. The bot list uses bounded 100-record pages with a load-more control, so Unlimited
accounts can reach configurations beyond the first page. A downgrade does not
delete existing records.
Over-limit accounts can read, pause and archive; new creation stays refused
until capacity is available. Account deletion retains its cancellation checks.

Daily quotas count completed backtests, using the reservation's UTC day and a
00:00 UTC reset. A conditional D1 insert atomically reserves the daily credit and
one in-flight request per user. Entitlement/validation/configuration refusals do
not reserve a credit. Provider errors, invalid responses and timeouts release
the reservation. Successful canonical `complete` responses consume one credit.
Abandoned reservations expire after five minutes; the Worker upstream timeout
is twenty seconds. Cleanup retains at most the current and previous UTC day.
Unlimited counts never remove authentication, risk rules, request bounds,
leverage/capital limits, engine cache bounds or the one-request concurrency cap.

Migration `0003_subscription_tiers.sql` adds plan identity and the per-user usage
ledger, plus a short webhook-reconciliation lease table. Existing subscriptions have no inferred plan and fail closed for paid
features until a signed webhook reconciles their canonical Stripe Price. This
migration never starts trials or changes records into live bots. A canonical
subscription must contain one supported Price with quantity one. Price metadata and browser/event plan labels
never grant entitlement. Unknown/multiple Prices produce `plan_mismatch`.

Nonterminal webhook reconciliation acquires a per-subscription lease before
fetching canonical Stripe state. The lease lasts thirty seconds; D1 evaluates
expiry with SQLite `unixepoch()`, including at each write. Contending events
receive HTTP 503 without a handled-event receipt, so Stripe can retry them.
The current owner and unexpired lease fence the subscription, trial-use and
receipt writes. Late owners cannot overwrite a replacement or release its
lease. Successful and failed processing release only their owned lease.
Cancellation events bypass this lease and retain the terminal-state guard, so
an in-flight plan update cannot delay cancellation or restore canceled access.
Lease rows contain only a SHA-256 subscription key, a random owner token and an
expiry. They have no wallet, customer or user fields. Release and expiry cleanup
manage their lifecycle independently of account deletion.

The three Price bindings must be distinct. Configure all Prices, portal, secret
key and webhook secret in the same Stripe mode. Test-mode Products/Prices and a
portal configuration do not establish live billing readiness. No real Price IDs
or bearer credentials are committed. Both Wrangler configurations set
`BILLING_LAUNCH_ENABLED` to `false`; do not open Checkout before the public engine,
customer execution boundaries and billing acceptance are verified. Cancellation
and signed webhook processing remain independent of that launch gate.

## Cloudflare layout

`website/wrangler.jsonc` defines one Worker, static assets, the account D1 binding,
an expiry-cleanup cron and custom domains for oraclebot.io and www.oraclebot.io.
The Worker handles API requests and applies security headers to assets. The
www host redirects to the canonical origin. D1 stores accounts, challenges,
sessions, subscriptions, webhook receipts and paper bot definitions.

Cloudflare Workers can call Coinbase, Jupiter, Stripe and other HTTPS APIs.
External providers still require their own authentication, permissions, limits
and availability. A connected wallet is not a Coinbase API authorization and a
Jupiter Swap quote is not a leveraged perpetual position.

The Python engines use normal CPython and NumPy/pandas. Run them in a separate
container service or Cloudflare Containers, behind HTTPS and a secret bearer
credential. Ordinary edge Worker requests are not a persistent trading daemon.
No tunnel to the owner's existing loopback UI is configured. The adapter only
accepts named public-market analysis operations. Provisioning it does not by
itself provision live trading.

## Development and checks

From `website/`, use Node 22.13 or newer:

```sh
npm ci
npm run db:local
npm run dev
npm test
npm run check
```

Open the local URL printed by Wrangler. The development configuration binds `APP_ORIGIN` to `http://localhost:8799`
and omits production custom-domain routes. Override it in the development
configuration if you change the local port.
Use HTTPS in a normal browser for wallet authentication and the secure session
cookie. The automated tests exercise authentication without a wallet extension.
There are no runtime npm dependencies. Wrangler and Playwright are pinned
development tools. The browser regression suite serves local fixtures and never
contacts wallets, Stripe or trading venues:

```sh
npx playwright install chromium
npm run test:browser
```

Set `CHROME` to an existing Chromium executable to use that browser instead.
CI installs the matching Playwright Chromium and runs this suite.

From the repository root, run the Python engine tests and exporter verification
using an environment with the canonical packages installed:

```sh
python3 -m unittest website.engine.test_server website.engine.test_research
python3 -m website.scripts.export_research --check
```

The existing component suites remain the gates for changes to their own engines.
The website adapter does not change signal generation, fills or order execution.

## Production configuration

Nonsecret bindings:

| Binding | Purpose |
| --- | --- |
| `DB` | Account D1 database |
| `ASSETS` | Static asset collection |
| `APP_ORIGIN` | Exact canonical HTTPS origin, domain-bound wallet challenges |
| `APP_VERSION` | Deployed application version |
| `BILLING_LAUNCH_ENABLED` | Exact string `true` opens new Checkout; omitted or any other value keeps it closed |
| `STRIPE_STARTER_PRICE_ID` | Server-only allowlisted Starter recurring USD monthly Price |
| `STRIPE_ADVANCED_PRICE_ID` | Server-only allowlisted Advanced recurring USD monthly Price |
| `STRIPE_UNLIMITED_PRICE_ID` | Server-only allowlisted Unlimited recurring USD monthly Price |
| `STRIPE_PORTAL_CONFIGURATION_ID` | Explicit cancellation/payment-management portal configuration (`bpc_…`) |
| `ENGINE_URL` | HTTPS base URL of the read-only analysis adapter |

Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` and `ENGINE_TOKEN` as Worker
secrets through Wrangler. Never put values in the repository, browser, D1 bot
configuration, logs or chat. Use test mode until signed Checkout, subscription,
cancellation and entitlement behavior have been verified end to end.

Configure Stripe to send `checkout.session.completed` and
`customer.subscription.created`, `.updated` and `.deleted` to
`https://oraclebot.io/api/billing/webhook`. Configure the Stripe customer portal
for cancellation and payment-method management. Portal sessions always include the
configured portal ID. Existing customers can open the portal while new Checkout
is disabled; portal availability requires only the customer, secret key and portal
configuration. The handler verifies raw-body
HMAC signatures and fetches the canonical subscription before updating access.

For an authenticated Cloudflare deployment from `website/`:

```sh
npm run db:remote
npm run deploy
```

Verify `https://oraclebot.io/api/health`, then exercise the actual deployed
website. A true `storage` binding flag does not replace the wallet round-trip
and database verification. Successful source checks do not establish successful
external payments, fresh Oracle inputs or live orders.

## Rollback

Deploy the previous Worker version using Cloudflare version rollback. Preserve
D1 data; this initial schema is additive. Bot definitions cannot place orders,
so rolling back this website cannot require cancelling venue orders.
