# Copilot instructions

## Default Execution Strategy

Read [CLAUDE.md](../CLAUDE.md) before proposing a change. It is the source of truth for this
repository; this file is a pointer plus the rules that get broken most often.

1. **Identify the component first.** The correct level of caution differs by an order of
   magnitude between them.
2. **Do not weaken a safety default.** Dry-run stays the default; the extension installs
   disarmed.
3. **Verify before claiming.** Run the suites below and paste real output. A passing
   suggestion that was never run is worse than no suggestion.
4. **Prefer refusing to guessing.** In the money path, a missing number must surface as an
   error, never as a default or a zero.

## Components and their risk

| Component | Language | Risk |
| --- | --- | --- |
| `backtester/` | Python 3.13 | Simulation only. **Never add live-trading capability here.** The danger is a dishonest backtest, not a lost trade |
| `research/` | Python 3.13 | Analysis built on the backtester. The danger is overstating a result |
| `soltui/` | Python 3.13 | Read-only macOS menu-bar app and TUI. Places no orders |
| `extension/` | JavaScript (ESM) | **Can place real orders and move real money.** Production software |

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

## Verification

```bash
python3 -m unittest discover -s backtester/tests -t .   # 454 tests
python3 -m unittest discover -s soltui/tests -t .       # 95 tests (~70s)
cd extension && npm test                                # 114 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must close positive
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
```

The unpacked Chrome load cannot be automated, so never report it as verified. The headless
dry run is the integration gate.

## Style

**Python** — 3.13, stdlib-first, `from __future__ import annotations`, type hints, `unittest`
(not `pytest`). Dependencies are deliberately minimal; `pyarrow`, `requests` and `pytest`
are excluded on purpose.

**JavaScript** — ESM, no build step, **zero runtime dependencies**. Do not suggest a package
for something `src/wallet/solana.js` already solves. Tests are `node:test` +
`node:assert/strict`. Keep `src/core/grid.js`, `risk.js` and `pnl.js` free of I/O and
`chrome.*`.

**Both** — comments explain *why*, especially where the obvious implementation is wrong (MV3
timers, base58 zero bytes, FIFO vs paired-lot attribution, one-bar leaks). Do not narrate
*what*.

## Known-unverified areas

No live order has ever been placed, the Trigger order-list response envelope is guessed, and
fee attribution is unconfirmed. See `docs/known-issues.md`. Do not present any of them as
working.
