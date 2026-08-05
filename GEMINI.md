# GEMINI.md

Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file
first — it is the single source of truth, and this file only points at it.

## Know which component you are in

| Component | Risk |
| --- | --- |
| `backtester/` (Python) | Simulation only. **Never add live-trading capability.** The danger is a dishonest backtest |
| `research/` (Python) | Analysis on the backtester. The danger is overstating a result |
| `soltui/` (Python) | Read-only macOS display. Places no orders |
| `extension/` (JavaScript) | **Can place real orders and move real money.** Treat every change as production software |

## The rules most often broken here

- Dry-run is the default and the extension installs disarmed. Do not change a default such
  that a fresh install can place an order.
- Risk rails are enforced in `extension/src/core/risk.js` and must **fail closed** — a
  missing or NaN state field must not silently disable one.
- Never guess a price, quantity or fee that becomes an order. Refuse and surface it. Do not
  fall back to config, and do not fall back to zero.
- Reconcile against the venue before planning. An intent submitted but not live becomes
  `unknown` and is **never** auto-retried.
- Add actions to `extension/src/core/commands.js` only — three surfaces, one registry.
- No secret material in logs, `chrome.storage.sync`, the DOM, or a response body.
- No lookahead: a signal at bar `t` may use data only through bar `t`. Any change to signal
  generation or fill timing needs a test that would catch a one-bar leak.
- A new strategy ships `backtester/strategy_cards/<id>.md` in the same commit.
- `backtester/core/gridsim.py` and `extension/src/core/grid.js` must agree on economics.

## Before claiming a change works

```bash
python3 -m unittest discover -s backtester/tests -t .   # 454 tests
python3 -m unittest discover -s soltui/tests -t .       # 95 tests (~70s)
cd extension && npm test                                # 114 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must close positive
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
```

Loading the extension unpacked cannot be automated (`chrome://extensions` needs a human).
Do not claim it as verified — the headless dry run is the integration gate instead.

## House style

Python 3.13, stdlib-first, `from __future__ import annotations`, `unittest` not `pytest`.
JavaScript ESM with **zero runtime dependencies** and `node:test`. Comments explain *why*,
especially where the obvious implementation is wrong. Do not narrate *what*.

## Orientation

`docs/codebase-overview.md` for the file map, `docs/COMPONENTS.md` for module shapes,
`docs/known-issues.md` for what is already known to be broken.
