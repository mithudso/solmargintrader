# Security

This is a personal repository with no deployed service and no users other than its
author. There is no security mailbox and no disclosure SLA. Report anything you find by
opening an issue, or directly to the repository owner.

## What is actually at risk here

The extension **can place real orders and move real money**. That makes three things
security-relevant in a way the rest of the repo is not:

| Asset | Where it lives | Rule |
| --- | --- | --- |
| Jupiter API key | `chrome.storage.local` only | Never `chrome.storage.sync`, never a log, never a response body. `setApiKey` returns a length, never the key |
| Session-key vault | `chrome.storage.local`, or a mode-0600 file (`src/storage/fileStore.js`) | Same |
| Local HTTP API | `extension/tools/api-server.js`, bound locally | Requires `SMT_API_TOKEN`; treat the port as trusted-local only |

`SMT_API_TOKEN`, `SMT_PASSPHRASE` and `JUPITER_API_KEY` are read from the environment by
the tools. Real values belong in a local `.env` that is gitignored — see `.env.example`
for the shape. Never commit one.

## Reporting something that could move money

Say so plainly and in the title. A missing risk rail, a path that guesses a price or
quantity, or an intent that auto-retries after a crash are all in this category, because
each of them can cause an order nobody asked for.

## Non-goals

- The backtester and research components do not touch the network during a run and place
  no orders. A bug there is a correctness bug, not a security one.
- `soltui/` is read-only over the research side.
- No live order has ever been placed by this extension. See the **Verification status**
  section of `extension/README.md` before treating any live-path behaviour as proven.
