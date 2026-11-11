# Volty prospective paper watcher

Version: 1.0.1. Delta: independently reviewed post-commit durability and immutable specification provenance; retire the initial unverified cohort.

The watcher observes the exact TradingView chart parameters (length 5, multiplier
1, one minute) and the five previously frozen study configurations. Each account
starts with fresh simulated capital. It never loads a wallet, signs, places an
order, or promotes a configuration. The existing ZEC ensemble service and shared
SolTUI prediction producer keep their own ownership and state.

This is a **Binance ZECUSDT OHLC reference experiment**, using the existing Volty
simulator at 1x. It does not reproduce the private TradingView chart's fills or
Jupiter ZEC/USDC execution at 2x with 75% collateral. The frozen configurations use
10 bps fees, 2 bps slippage per side and a synthetic 0.1 bps/hour carry scenario.
Actual Jupiter funding and executable liquidity remain unverified inputs to that
comparison. USDT prices are not silently converted into USDC prices.

## Causal observation and persistence

The watcher reads the specification bytes once, then parses and hashes that same
immutable buffer. Replacing the file during network warmup cannot bind one
configuration to another file’s digest.

The watcher reads closed candles from Binance's public market-data-only endpoint.
Native 1m, 5m, 1h and 1d candles retain their UTC alignment. Complete pairs of native
5m candles form 10m candles; missing halves never become invented bars.

The watcher records each stop's source bar, issue time and first eligible bar
in SQLite before that eligible bar opens. A decision becomes eligible only after
its immutable row commits with SQLite `synchronous=FULL`. A separate confirmation
records a fresh timestamp sampled after that first commit returned. The scorer
requires a committed confirmation with `durable_at` strictly before the eligible
bar. A crash before confirmation leaves the decision ineligible. Restart blocks
that account instead of confirming it retrospectively. A closed bar arrives after
its close,
so the prospective experiment deliberately adds **one whole bar of signal delay**
to the simulator's ordinary next-bar stop rule. This is an execution-latency
scenario, not a claim of Pine fill parity. Historical seed bars only warm the
indicator. The first future activation bar is frozen when the cohort starts.

The simulator keeps open paper positions between observations. It replays the
same retained causal prefix and frozen costs, with no artificial close on every
poll. SQLite atomically retains candles, issued stops, cursors and account
snapshots. A restart resumes those records and the same start boundary; it does
not refit parameters or backfill missed prospective decisions. A second worker
for the same cohort cannot acquire its kernel-held file lock.

If an outage misses a decision window, a candle changes, source history has a gap,
or the bound simulator/watcher implementation changes, the cohort stops producing
valid new paper evidence. Status exposes the block and retains earlier snapshots.
A transient feed failure can recover only while the next decision window remains
open. A cohort is bounded to 100,000 retained candles per interval because prefix
replay grows with its observation history; reaching that limit requires review.

## Installed service

The owner-authorized installation uses regular installed packages in a separate
stable virtual environment, not an editable source tree or temporary worktree.
The per-user launchd LaunchAgent starts at login and restarts a failed worker.
It runs as the owner without root privileges; it is not a pre-login LaunchDaemon.

| Artifact | Absolute path |
| --- | --- |
| Interpreter | `/Users/mitch/.venvs/volty-forward-20261111/bin/python` |
| Durable cohort | `/Users/mitch/.local/share/solmargintrader/volty-forward-20261111-v2/volty-forward.sqlite3` |
| Worker log | `/Users/mitch/.local/share/solmargintrader/volty-forward-20261111-v2/daemon.log` |
| LaunchAgent | `/Users/mitch/Library/LaunchAgents/com.solmargintrader.volty-forward.dec374f4ccc8.plist` |
| Private installation evidence | `/Users/mitch/.local/state/soloracle-tradingview/volty-forward-20261111-v2/` |

Read-only status:

```bash
/Users/mitch/.venvs/volty-forward-20261111/bin/python -I -m ecosystem.volty_forward --home /Users/mitch/.local/share/solmargintrader/volty-forward-20261111-v2 status
launchctl print gui/501/com.solmargintrader.volty-forward.dec374f4ccc8
```

To stop this paper watcher persistently, disable and unload only its own job:

```bash
launchctl disable gui/501/com.solmargintrader.volty-forward.dec374f4ccc8
launchctl bootout gui/501/com.solmargintrader.volty-forward.dec374f4ccc8
```

The cohort remains on disk. Re-enable and bootstrap the same plist to resume;
the worker will refuse missed windows rather than manufacturing an unobserved
track record. A new cohort requires an explicit new home and fresh initialization.
Neither restarting the watcher nor funding the trading wallet authorizes changing
its frozen paper book into a live strategy.

## Verification and limits

The focused suite is:

```bash
cd /Users/mitch/dev/solmargintrader
/Users/mitch/.venvs/soloracle/bin/python -m unittest ecosystem.tests.test_volty_forward research.tests.test_volty_zec -q
ruff check ecosystem/volty_forward.py ecosystem/tests/test_volty_forward.py backtester/core/volty.py
```

It checks lock acquisition, replay and actual SQLite commit delays during
initialization and ticks; crash-before-confirmation; immutable decisions;
concurrent specification replacement; future-data mutation; delayed stop
eligibility; open-book costs; frozen initialization; durable cursor/restart, duplicate polls and workers, outage blocks,
implementation binding, complete native candle aggregation and launchd rendering.
These checks establish accounting and lifecycle behavior. Prospective profitability
needs an adequate future sample; source tests and a running service establish no
profitable edge.

Binance's current public contract was checked through its official Spot API
documentation. The supported native intervals exclude 10m:

https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md

https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md

## Retired initial cohort

The initial cohort at `/Users/mitch/.local/share/solmargintrader/volty-forward-20261111/` is retained as **unverified durability evidence**. Its LaunchAgent `com.solmargintrader.volty-forward.a9c5bedfae26` is disabled and unloaded. Independent review showed that its pre-commit timestamp did not prove a decision was durable before the eligible bar opened. Do not count its snapshots as verified prospective results, copy them into v2, or restart that service. The v2 cohort has a separate store, new activation boundaries and post-commit confirmations.
