# CLAUDE.md — solmargintrader

Instructions for agents working in this repository. Read before changing code.

## What this is

Three components with different risk profiles. Know which one you are in:

| Component | Risk |
| --- | --- |
| `backtester/` (Python) | Simulation only. **Never add live-trading capability here** — see its README's Scope section. The danger is a dishonest backtest, not a lost trade. |
| `research/` (Python) | Analysis built on the backtester. The danger is overstating a result. |
| `extension/` (JavaScript) | **Can place real orders and move real money.** Treat every change as production software. |

## Non-negotiables — extension

1. **Dry-run stays the default.** `DEFAULT_CONFIG.mode` is `dry-run` and the extension installs
   disarmed. Never change a default so a fresh install can place an order.
2. **Risk rails live in code.** Every rail is a gate in `src/core/risk.js` that an order must pass. A
   rail documented but not enforced is not a rail. Rails must **fail closed** — a missing or NaN
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
   message handler, CLI branch or HTTP route carrying its own logic — `test/surfaces.test.js` will
   fail, and correctly so.
7. **The exit is one rung above the entry.** A sell placed at the level it was bought at captures
   zero and pays two fees. `expectedRoundTripUsd` and its test exist because this bug shipped once.

## Non-negotiables — backtester

1. **Correctness of the simulation outranks the number of strategies.** A tool that honestly reports
   a losing strategy is a success; one that reports an inflated Sharpe from a leaked bar is a
   failure even if it runs.
2. **No lookahead.** A signal at bar *t* may only use data through bar *t*. Any change touching
   signal generation or fill timing needs a test that would catch a one-bar leak.
3. **Costs are never optional.** Fees, slippage and the perp borrow fee stay in the P&L path.
4. **The engine does not touch the network.** Fetching is a separate, explicit step
   (`backtester.core.fetch`) writing a local cache.
5. **Every registered strategy has a card.** `backtester/strategy_cards/<id>.md` carries its
   equations, reasoning, limitations and parameter defaults, and `tests/test_strategy_cards.py`
   checks the machine-readable half against the code in both directions — a registry entry with no
   card fails, and so does a card whose defaults have drifted. Add the card in the same commit as
   the strategy.
6. **The ladder grid must agree with the extension.** `core/gridsim.py` is a port of
   `extension/src/core/grid.js`; a change to either one's economics needs the matching change in the
   other, or the backtest becomes a confident wrong number about the live strategy. Do not confuse it
   with the `grid` strategy in `core/strategies/signals.py`, which is an exposure staircase, not a
   ladder of resting orders.

## Before you claim a change works

```bash
python3 -m unittest discover -s backtester/tests -t .   # 514 tests
python3 -m unittest discover -s soltui/tests -t .       # 95 tests (~70s)
cd extension && npm test                                # 131 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must still close positive
node tools/verify-endpoints.js                          # live Jupiter reachability
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
```

Loading the extension unpacked cannot be automated (`chrome://extensions` needs a human). Do not
claim it as verified — the headless dry run is the integration gate instead.

## House style

**JavaScript** — ESM, no build step, **zero runtime dependencies**. Do not add a package to solve
something the ~150 lines of `src/wallet/solana.js` already solve. Tests are `node:test` +
`node:assert/strict`. Keep `src/core/grid.js`, `risk.js` and `pnl.js` free of I/O and `chrome.*`.

**Python** — 3.13, stdlib-first. Dependencies are declared in `backtester/requirements.txt` and kept
minimal on purpose (`pyarrow`, `requests` and `pytest` are deliberately excluded; tests use
`unittest`). Type hints with `from __future__ import annotations`.

**Both** — comments explain *why*, especially where the obvious implementation is wrong (MV3 timers,
base58 zero bytes, FIFO vs paired-lot attribution, one-bar leaks). Do not narrate *what*.

## Known-unverified areas

Read "Verification status" in `extension/README.md` before extending it. In short: **no live order
has ever been placed**, the Trigger order-list response envelope is guessed, and fee attribution is
unconfirmed. Do not present any of them as working.

## Related

`AGENTS.md` points here. Component detail lives in `backtester/README.md` and
`extension/README.md`; cross-cutting detail in `docs/`.
