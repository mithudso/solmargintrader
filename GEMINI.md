# GEMINI.md

Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file
first — it is the single source of truth, and this file only points at it.

Save requests in `prompts.md` and versioned continuation records in `memory.md`, as
`CLAUDE.md` requires. Gemini shares those rules; this repo defines no Gemini-only tools.

## Know which component you are in

| Component | Risk |
| --- | --- |
| `backtester/` (Python) | Simulation only. **Never add live-trading capability.** The danger is a dishonest backtest |
| `research/` (Python) | Analysis on the backtester. The danger is overstating a result |
| `soltui/` (Python) | Read-only macOS display. Places no orders |
| `mongo/` (Python) | Derived local datastore plus a query reference. Rebuildable; nothing else imports it |
| `extension/` (JavaScript) | **Can place real orders and move real money.** Treat every change as production software |
| `liquidity/` (Python, own venv) | **Can move real money on Base.** Read `liquidity/CLAUDE.md` first |

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
python3 -m unittest discover -s backtester/tests -t .   # 909 tests
python3 -m unittest discover -s soltui/tests -t .       # 1181 tests (~840s, optional)
python3 -m unittest discover -s mongo/tests -t .        # 34 tests
cd extension && npm test                                # 361 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must close positive
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
```

`cd extension && npm run e2e` loads the unpacked extension in Chrome for Testing and checks
loading and dry-run behaviour only (it never arms or signs). Do not claim live execution as
verified — the headless dry run is the economics gate.

## House style

Python 3.13, stdlib-first, `from __future__ import annotations`. Backtester, soltui and
mongo use `unittest`; liquidity uses `pytest` and Ruff in its own virtualenv.
JavaScript ESM with **no npm runtime dependencies** (one vendored, pinned charting library:
`extension/vendor/lightweight-charts/`) and `node:test`. Comments explain *why*,
especially where the obvious implementation is wrong. Do not narrate *what*.

## Orientation

`docs/codebase-overview.md` for the file map, `docs/COMPONENTS.md` for module shapes,
`docs/known-issues.md` for what is already known to be broken.
