## Default Execution Strategy

Read [CLAUDE.md](../CLAUDE.md) before proposing a change. It is the source of truth for this
repository; this file is a pointer plus the rules that get broken most often.

1. Read relevant source before editing; never invent a command or path.
2. Save requests in `prompts.md` and update versioned `memory.md` continuation notes.
3. Run the applicable verification commands after changes.
4. **Identify the component first.** The correct level of caution differs by an order of
   magnitude between them.
5. **Do not weaken a safety default.** Dry-run stays the default; the extension installs
   disarmed.
6. **Verify before claiming.** Run the suites below and paste real output. A passing
   suggestion that was never run is worse than no suggestion.
7. **Prefer refusing to guessing.** In the money path, a missing number must surface as an
   error, never as a default or a zero.

## High-level Architecture

| Component | Language | Risk |
| --- | --- | --- |
| `website/` | JavaScript ESM/Python | Public wallet accounts and optional Stripe charges; trading definitions inactive, analysis adapter read-only |
| `backtester/` | Python 3.13 | Offline simulation; no live trading |
| `research/` | Python 3.13 | Analysis and prospective paper evidence; no live trading |
| `oracle/` | Python 3.13 | Shadow forecasts and read-only MCP; separately enabled TradingView worker can submit Coinbase spot or GUM ZEC perpetual orders |
| `botmanager/` | Python 3.13 | Fenced paper accounts, lifecycle and evidence; no signing |
| `ecosystem/` | Python 3.13 | Paper coordination and authenticated local control room; no order submission |
| `soltui/` | Python 3.13 | Research console with a separately armed manual Coinbase spot path; Jupiter V2 submit remains blocked |
| `mongo/` | Python 3.13 | Rebuildable derived storage; no execution dependency |
| `extension/` | JavaScript ESM | Live-capable order paths behind separate rails; installs dry-run/disarmed |
| `executor/` | Python, own environment | Guarded Solana spot swaps; read `executor/CLAUDE.md` |
| `liquidity/` | Python, own environment | Base LP code retained; daemon archived, disabled and killed |

The webhook's venue worker is independent of Oracle's prediction and timeframe
votes. Read `docs/JUPITER-ZEC-WEBHOOK.md` before changing its account, signing or
funding boundary. Do not enable live mode during a code audit.

## Non-negotiables — extension

- `DEFAULT_CONFIG.mode` is `dry-run`. A fresh install must not be able to place an order.
- Every risk rail is a gate in `src/core/risk.js`. A rail documented but not enforced is not
  a rail, and rails must **fail closed** on missing or NaN state (`normaliseState`).
- Never guess a price, quantity or fee that becomes an order. No config fallback, no zero
  fallback.
- Reconcile before plan. The venue's live order list is the truth; local state is a cache.
  A submitted-but-not-live intent becomes `unknown` and is **never** auto-retried.
- No secret material in logs, `chrome.storage.sync`, the DOM, or a response body. The API
  key and session-key vault are `chrome.storage.local` or a mode-0600 file only.
- Three surfaces, one registry: every action belongs in `src/core/commands.js`.
  `test/surfaces.test.js` fails otherwise, and correctly so.
- The exit rests one rung **above** the entry. Selling at the level you bought captures zero
  and pays two fees; `expectedRoundTripUsd` exists because that shipped once.

## Non-negotiables — backtester

- Correctness of the simulation outranks the number of strategies.
- **No lookahead.** A signal at bar `t` may use data only through bar `t`. Any change to
  signal generation or fill timing needs a test that would catch a one-bar leak.
- Costs are never optional: fees, slippage and the perp borrow fee stay in the P&L path.
- The engine does not touch the network. Fetching is a separate explicit step.
- Every registered strategy has a card in `backtester/strategy_cards/`, added in the same
  commit.
- `core/gridsim.py` is a port of `extension/src/core/grid.js`; a change to either one's
  economics needs the matching change in the other.

## Build, Test, and Validation Commands

```bash
python3 -m unittest discover -s backtester/tests -t .   # 1120 tests
python3 -m unittest discover -s soltui/tests -t .       # 1579 tests (TUI dependencies required)
python3 -m unittest discover -s mongo/tests -t .        # 57 tests
cd extension && npm test                                # 483 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must close positive
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
python3 -m unittest discover -s oracle/tests -t . -v
ruff check oracle
python3 -m unittest discover -s ecosystem/tests -t . -v
ruff check ecosystem oracle scripts/bootstrap_ecosystem.py
npm --prefix website test
npm --prefix website run check
python3 -m unittest website.engine.test_server website.engine.test_research
python3 -m website.scripts.export_research --check
```

`cd extension && npm run e2e` verifies an unpacked extension in a temporary Chrome
for Testing profile. The separate `tools/control-room-e2e.mjs` gate verifies the
installed native helper and nontrading server recovery. Neither proves a personal
Chrome profile was updated or that live orders work.

## Key Conventions

**Python** — 3.13, stdlib-first, `from __future__ import annotations`, type hints.
Backtester, research, soltui and mongo use `unittest`. Liquidity has its own `pytest`,
Ruff and locked dependencies; verify from `liquidity/` with `.venv/bin/ruff check src tests`
and `.venv/bin/pytest -q`. The backtester deliberately excludes `pyarrow`, `requests`,
and `pytest`.

**JavaScript** — ESM, no build step, no npm runtime dependencies. The sanctioned
vendored TradingView Lightweight Charts 5.2.1 build is pinned under
`extension/vendor/lightweight-charts/`; read its README before changing it. Do not suggest a package
for something `src/wallet/solana.js` already solves. Tests are `node:test` +
`node:assert/strict`. Keep `src/core/grid.js`, `risk.js` and `pnl.js` free of I/O and
`chrome.*`.

**Both** — comments explain *why*, especially where the obvious implementation is wrong (MV3
timers, base58 zero bytes, FIFO vs paired-lot attribution, one-bar leaks). Do not narrate
*what*.

## Known-unverified areas

The extension Trigger live path remains unverified, including authenticated wallet
responses, execution USD valuation and fee attribution. Its bundled signer lacks a
Trigger semantic verifier. Oracle's GUM order Action verifier is a separate boundary;
it does not verify arbitrary funding transactions. Unit tests and a successful
preflight do not prove live fills or a profitable strategy. See `docs/known-issues.md`
and `docs/JUPITER-ZEC-WEBHOOK.md`.

## Hosted website boundaries

`website/README.md` defines the Cloudflare account, billing and analysis layout.
Wallet sign-in is account authentication, not delegated trading authority. Keep
Stripe and engine credentials server-side. Membership entitlement comes from the
verified subscription, not a Checkout redirect. Saved paper configurations do
not start workers or authorize live Coinbase/Jupiter orders.
