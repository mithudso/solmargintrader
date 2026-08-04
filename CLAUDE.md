# CLAUDE.md — solmargintrader

Instructions for agents working in this repository. Read before changing code.

## What this is

A grid-trading system for Jupiter on Solana, delivered as a Chrome MV3 extension plus a CLI and a
local HTTP API. It can move real money. Treat every change as production software.

## Non-negotiables

1. **Dry-run stays the default.** `DEFAULT_CONFIG.mode` is `dry-run` and the extension installs
   disarmed. Never change a default so that a fresh install can place an order.
2. **Risk rails live in code.** Every rail is a gate in `src/core/risk.js` that an order must pass.
   A rail documented but not enforced is not a rail. Rails must **fail closed** — a missing or NaN
   state field must not silently disable one (see `normaliseState`).
3. **Never guess a number that becomes an order.** If a price, quantity or fee is missing or
   unusable, refuse and surface it. Do not fall back to config, and do not fall back to zero.
4. **Reconcile before plan.** The venue's live order list is the source of truth at the top of every
   tick; local state is a cache. An intent that was submitted but is not live becomes `unknown` and
   is **never auto-retried** — that is how a rung double-fires after a crash.
5. **No secret material in logs, `chrome.storage.sync`, the DOM, or a response body.** The API key
   and the session-key vault are `chrome.storage.local` / mode-0600 file only. `setApiKey` returns a
   length, never the key.
6. **Three surfaces, one registry.** Every action belongs in `src/core/commands.js`. Do not add a
   message handler, CLI branch or HTTP route with its own logic — the parity test in
   `test/surfaces.test.js` will fail, and correctly so.
7. **The exit is one rung above the entry.** A sell placed at the level it was bought at captures
   zero and pays two fees. `expectedRoundTripUsd` and its test exist because this bug shipped once.

## Before you claim a change works

```bash
cd extension
npm test                                              # must be green; report the real count
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # a round trip must still close positive
node tools/verify-endpoints.js                        # live Jupiter reachability
```

Loading the extension unpacked cannot be automated (`chrome://extensions` needs a human). Do not
claim it as verified — use the headless dry run as the integration gate instead.

## House style

- ESM modules, no build step, **zero runtime dependencies**. Do not add a package to solve something
  ~150 lines of `src/wallet/solana.js` already solves.
- Tests are `node:test` + `node:assert/strict`. No test framework dependency.
- Comments explain *why*, especially where the obvious implementation is wrong (MV3 timers,
  base58 zero bytes, FIFO vs paired-lot attribution). Do not narrate *what*.
- Keep pure logic pure: `src/core/grid.js`, `risk.js` and `pnl.js` take no I/O and no `chrome.*`.

## Known-unverified areas

Read the "Verification status" section of `extension/README.md` before extending these. In short: no
live order has ever been placed, the order-list response envelope is guessed, and fee attribution is
unconfirmed. Do not present any of them as working.

## Related

`AGENTS.md` is a pointer to this file. Deeper detail lives in `docs/`.
