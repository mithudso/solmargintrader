# Coin suitability and backtest audit

The Bots tab has **Rank all coins (quick)** and **Audit selected coin** controls
for the grid and averaging-down DCA bots. Ranking uses every coin in the local
cache, retains missing/error rows, and sorts candidates by historical fit and the
stated score. Selecting a row shows its reasoning, all22 template fields, equity
and buy-and-hold curves. Auditing it uses the frozen quick configuration/window
and shows ten base/stress scenarios without changing the quick order or score.
The triangle bot is unsupported for this coin screen; its existing backtest and
optimizer remain available. Scheduled accumulation is available through the CLI.

Jobs run in an owned background worker. Progress, cancellation, stale-result
protection and teardown do not block the TUI or start trading. A cancelled,
failed or interrupted job cannot appear completed. No config is auto-adopted.

## Command line

```sh
python scripts/coin_strategy_fit.py --coin SOL --bot grid --mode quick
python scripts/coin_strategy_fit.py --coins SOL BTC ETH --bot dca --mode quick --format csv
python scripts/coin_strategy_fit.py --coin SOL --bot grid --mode audit --format json --output coin-audit.json
python scripts/coin_strategy_fit.py --demo --bot all --mode audit
```

The CLI, reusable skill and command registry call the same backend. Use the
existing SolTUI Python environment and `--data-dir` for an explicit CSV cache.
The skill entrypoint is `skills/coin-strategy-fit/SKILL.md`; install that folder
by symlink in the standard Codex skill directory to retain its repository layout.
Its bundled script works from any current directory.

The full assumptions, schema, default heuristic thresholds and output meanings
are in `skills/coin-strategy-fit/references/method.md`.

## Verification

```sh
python -m unittest backtester.tests.test_coinfit soltui.tests.test_coin_fit soltui.tests.test_coin_fit_ui -v
python scripts/coin_strategy_fit.py --demo --bot all --mode audit --format json --output /tmp/coin-fit-demo.json
```

The demo is deterministic synthetic data with explicit RANGE/RALLY/FALL names,
not results for real coins. A positive historical audit remains conditional on
its candle fill/cost model and is not live due-diligence approval.
