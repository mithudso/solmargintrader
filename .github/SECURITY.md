# Security

This repository contains personal research/execution tooling and a separate hosted
wallet-account website. There is no security mailbox and no disclosure SLA. Report anything you find by
opening an issue, or directly to the repository owner.

## What is actually at risk here

The extension **can place real orders and move real money**. That makes three things
security-relevant. The optional Oracle TradingView worker, executor and separately
armed SolTUI Coinbase path also move money. Liquidity retains a Base signing
boundary but its daemon is archived and disabled:

| Asset | Where it lives | Rule |
| --- | --- | --- |
| Jupiter API key | `chrome.storage.local` only | Never `chrome.storage.sync`, never a log, never a response body. `setApiKey` returns a length, never the key |
| Session-key vault | `chrome.storage.local`, or a mode-0600 file (`src/storage/fileStore.js`) | Same |
| Oracle webhook secret and GUM signing key | Private local process/file configuration; never committed | Default dry-run; authenticate ingress and verify owner-bound order Actions; see `docs/JUPITER-ZEC-WEBHOOK.md` |
| Liquidity signing key | Owner-only key file / macOS Keychain / legacy environment fallback | Agents never read, print or copy it; see `liquidity/CLAUDE.md` |
| Local HTTP API | `extension/tools/api-server.js`, bound locally | Requires `SMT_API_TOKEN`; treat the port as trusted-local only |
| Hosted accounts and sessions | Cloudflare D1, through `website/src/worker.js` | Single-use wallet challenges, hashed session tokens and tenant-scoped queries; never expose local owner services |
| Hosted billing and analysis credentials | Cloudflare Worker secrets | Never commit or expose Stripe secrets or `ENGINE_TOKEN`; see `website/README.md` |

`SMT_API_TOKEN`, `SMT_PASSPHRASE` and `JUPITER_API_KEY` are read from the environment by
the tools. Real values belong in a local `.env` that is gitignored — see `.env.example`
for the shape. Never commit one. These extension tools require exported environment variables; they
do not automatically source a `.env` file. See `docs/SECURITY.md` for the full threat model.

The separate raw-capture uploader can read its explicitly selected dotenv file for
`MONGODB_URI` or `MONGODB_URI2`. Keep that file and its X509 certificate private.
Hosted Worker secrets use Wrangler's secret store rather than the repository dotenv file.

## Reporting something that could move money

Say so plainly and in the title. A missing risk rail, a path that guesses a price or
quantity, or an intent that auto-retries after a crash are all in this category, because
each of them can cause an order nobody asked for.

## Non-goals

- The backtester and research components do not touch the network during a run and place
  no orders. A bug there is a correctness bug, not a security one.
- SolTUI's research runtime is paper-only. Manual Coinbase spot orders have a
  separately armed path; manual Jupiter V2 submission remains blocked pending
  independent economic transaction verification.
- No live order has ever been placed by this extension. See the **Verification status**
  section of `extension/README.md` before treating any live-path behaviour as proven.
