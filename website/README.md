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

The website can be deployed independently. Billing needs the owner's chosen
recurring price and Stripe configuration. Analysis needs a provisioned Python
engine with a public-market cache and a read-only Oracle archive. Live automated
Coinbase and Jupiter accounts need a separate implementation of per-user venue
authorization, isolated workers, risk enforcement, reconciliation and verified
signing. The website does not inherit the owner's existing trading authority.

Do not describe this release as a working paid live-trading service. The UI and
health API report these capabilities independently.

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
| `PRICE_LABEL` | Owner-approved renewal amount and interval |
| `STRIPE_PRICE_ID` | Owner-approved recurring subscription Price |
| `ENGINE_URL` | HTTPS base URL of the read-only analysis adapter |

Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` and `ENGINE_TOKEN` as Worker
secrets through Wrangler. Never put values in the repository, browser, D1 bot
configuration, logs or chat. Use test mode until signed Checkout, subscription,
cancellation and entitlement behavior have been verified end to end.

Configure Stripe to send `checkout.session.completed` and
`customer.subscription.created`, `.updated` and `.deleted` to
`https://oraclebot.io/api/billing/webhook`. Configure the Stripe customer portal
for cancellation and payment-method management. The handler verifies raw-body
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
