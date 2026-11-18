# Open the terminal interfaces and run repository scripts

On the existing Mac checkout, start in the repository and use its Python 3.13 SolTUI environment for local modules. If installed elsewhere, use that checkout's root and virtual environment. See the [installation guide](INSTALLATION.md) for a fresh setup and the [development guide](DEVELOPMENT.md) for dependency and test commands.

```sh
cd /Users/mitch/dev/solmargintrader
PY=/Users/mitch/.venvs/soltui/bin/python
"$PY" -V
```

## Open an interface

| Interface | Command | What opens |
| --- | --- | --- |
| SolTUI | `soltui` | The main terminal console on **Now**. Use **Research** to browse strategies and studies. |
| SolTUI classic | `soltui --classic` | The same console with the original tab bar, starting on **Backtest**. |
| Oracle Winners TUI | `"$PY" scripts/oracle_winners.py` | The Oracle terminal display with strategy signals, indicators and shapes. |
| Oracle paper and leverage panel | `"$PY" scripts/oracle_winners.py --leverage-panel` | The Oracle console opened on its paper forward and leverage controls. Opening the panel leaves trading authorization to the existing controls. |
| SolTUI in a browser | `soltui serve` | A browser terminal view served on loopback. Use `--no-open` to print the URL for manual opening. |
| SolTUI macOS menu bar | `soltui app` | The macOS indicator, using the console environment. |
| Managed paper control room | `solbot ui open` | The operational browser UI. The command starts the availability suite if needed. Run `solbot ui status` first to inspect the running instance without starting it. |

If `soltui` is missing from `PATH`, use `./soltui/bin/soltui` from the repository root, or use `"$PY" -m soltui.tui` for the terminal console. SolTUI's normal startup can connect to market streams and start its configured paper or research workers. The Oracle display also uses the configured market feed and saved preferences. To inspect arguments without opening either interface, run:

```sh
./soltui/bin/soltui --help
"$PY" scripts/oracle_winners.py --help
"$PY" scripts/oracle_winners.py --plain --help
solbot ui --help
```

The `--plain` and `--json` Oracle modes write to the terminal instead of drawing the TUI. The five-minute ZEC strategy card identifies a candidate in a historical Coinbase batch. The Oracle display and the SolTUI Compound 5m workspace have their own strategy selections.

See [SolTUI navigation](../soltui/README.md), [Oracle panel controls and paper state](ORACLE-LEVERAGE.md) and [the managed suite guide](bot-manager-managed-suite.md).

## Inspect or repeat the ZEC study

Verify the supplied batch offline. On a checkout that has the local archive, this checks the frozen manifests, provider normalization and generated reports:

```sh
"$PY" -m research.coin_week --output /Users/mitch/dev/solmargintrader/research/my-coins-study --phase verify
```

Start a separate, current Coinbase ZEC/USD study by fetching public candles into a new directory, then running the offline analysis. Change `RUN` if the example output already exists.

```sh
RUN=/Users/mitch/dev/solmargintrader/research/zec-usd-fresh
"$PY" -m research.coin_week --coin ZEC --quote USD --output "$RUN" --phase fetch
"$PY" -m research.coin_week --output "$RUN" --phase analyze
"$PY" -m research.coin_week --output "$RUN" --phase verify
```

The new report ranks the policies on its own validation window. To follow the same equal-weight policy through the new study, look up candidate `697f3b1dd4526147f43ca3d4` with `mode=baseline` in the five-minute strategy CSV. Use `--resume` with the existing output to continue an interrupted run under its frozen plan. Use `--coins ETH BTC ZEC HYPE SOL --quote USD` in the fetch command to study the full native-pair list in a new directory. See [the weekly runner guide](../research/papers/WEEKLY-COIN-STUDY.md) and [the ZEC analysis](../research/papers/ZEC-5M-MEAN-REVERSION.md).

## Run other common tools

From the repository root, run Python modules with `"$PY" -m ...` and standalone scripts with `"$PY" path/to/script.py`. Use the script's help and its component guide for inputs and outputs before starting a job.

```sh
# Offline simulator smoke test with 100 synthetic daily bars
"$PY" -m backtester.cli --synthetic 100 --start 2020-01-01 --strategy buy_and_hold --no-charts

# Candle download and offline backtest entry points
"$PY" -m backtester.core.fetch --help
"$PY" -m backtester.cli --help

# Research runners
"$PY" -m research.strategy_config_sweep --help
"$PY" -m research.reversal_shapes prepare --help
"$PY" -m research.reversal_shapes analyze --help
"$PY" -m research.zec_cycles --help
"$PY" -m backtester.voltycli --help

# Console, manager, Oracle CLI and ecosystem command listings
soltui list
solbot --help
"$PY" -m oracle.cli --help
solecosystem --help

# Text search without starting semantic indexing
INDEX_NO_AUTO=1 "$PY" index/search.py --text "mean reversion"

# Extension simulator without a live feed
(cd extension && node tools/dryrun.js --ticks 8 --osc 6 --offline 100 --assert-economics)
```

The simulator smoke test prints a historical-account summary for synthetic data. The extension dry run checks that the synthetic round trip closes with positive modeled P&L. See [the development command reference](DEVELOPMENT.md), [backtester options](../backtester/README.md), [Oracle commands](../oracle/README.md) and [the extension guide](../extension/README.md).
