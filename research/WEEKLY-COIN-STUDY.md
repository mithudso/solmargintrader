# Repeat the ZEC candle studies for another coin

Version: 1.0.0

The entry point downloads the latest seven days of completed Binance USDT spot
one-minute bars and runs the candle-supported ZEC analyses. ETH is the default.
It also downloads BTC and ZEC for matched-clock return correlations. Each run
freezes its time window, catalogue, source hashes, options and exact provider
responses. It never starts a forward trial or changes an execution service.

Use Python 3.13 with the dependencies already declared in
`/Users/mitch/dev/solmargintrader/backtester/requirements.txt`:

```bash
python -m research.coin_week --coin ETH --output /absolute/path/to/new-eth-study
python -m research.coin_week --coin SOL --output /absolute/path/to/new-sol-study
```

The output directory must be new. A run that stops retains successful download
pages and completed analysis stages. Resume the exact frozen window:

```bash
python -m research.coin_week --coin ETH --output /absolute/path/to/new-eth-study --resume
```

Acquisition and analysis are separately available. The analysis and verification
phases require no network:

```bash
python -m research.coin_week --coin ETH --output /absolute/path/to/new-eth-study --phase fetch
python -m research.coin_week --coin ETH --output /absolute/path/to/new-eth-study --phase analyze
python -m research.coin_week --output /absolute/path/to/new-eth-study --phase verify
```

Use `--venue coinbase` for the separate Coinbase USD contract, or retain the
default `--venue binance` for Binance USDT. A run never mixes venues or quote
currencies. USDT is not USD; monetary simulations remain in the source quote.
Use `--end 2026-11-17T17:00:00Z` to reproduce a specified completed UTC window,
`--days` to change the window, `--references BTC,ZEC` to change comparison coins,
and `--workers` to bound component computation. The default uses 1,999 null
replicates. `--candidate-limit` is an explicitly incomplete smoke-test subset;
the default of zero evaluates the complete frozen 1,707-template catalogue.
Resuming retains the original analytical options even if different defaults
are supplied later. A finished study is immutable; `--resume` verifies it.

The first ETH run and its measured findings are in
`/Users/mitch/dev/solmargintrader/research/eth-week-20261117/report.md`.

That directory publishes the report, chart, summary and independent audit. The
complete 78-artifact run is preserved losslessly in
`/Users/mitch/dev/solmargintrader/research/eth-week-20261117/artifacts.zip`.
The original complete local run remains at
`/Users/mitch/.local/share/solmargintrader/research/weekly-coin/ETH-20261117T1713Z-2571`.
To verify the published archive in a fresh directory:

```bash
python -m zipfile -e /Users/mitch/dev/solmargintrader/research/eth-week-20261117/artifacts.zip /Users/mitch/.local/share/solmargintrader/research/weekly-coin/ETH-20261117-reproduction
python -m research.coin_week --output /Users/mitch/.local/share/solmargintrader/research/weekly-coin/ETH-20261117-reproduction --phase verify
```

The transferred work includes the original ensemble and expanded spot catalogue;
six baseline, causal shape, frequency and control modes; 1m/5m/10m/1h cadences;
four cost scenarios; cash and passive controls; all 50 Volty settings with three
OHLC path sensitivities; all 20 canonical grid/DCA reference configurations on
supported cadences; spectrum and confirmed pivot diagnostics; frozen cycle
forecasts; and one/two-bar reversal, excursion and shape observations.

Every source study has an explicit entry in each run's coverage inventory.
Historical receive-time order-book replay, Oracle-basis barrier and exit50
studies, historical top50-universe analyses and daily CPCV need inputs that a
week of spot candles cannot supply. The original hourly/six-hour/daily shape
router also lacks its required selection history. The runner preserves these
exclusions instead of changing the meaning of those studies. It does not
reproduce ten prospective paper accounts or infer their forward performance.

The 60/20/20 chronological split keeps selection before the final window. A
policy needs ten validation exits before it can enter the validation-only
net-return ranking. No test-window reranking occurs. Broad strategy sweeps and
their short-window profits remain exploratory. The paired shape/frequency
comparison files retain the same-clock controls for every applicable template.

Future-return correlations use features known at the signal minute's close.
Each horizon uses nonoverlapping outcomes and purges outcomes that cross split
ends. An approximate block-permutation maximum-statistic correction spans all
validation/test features and horizons. The shortlist is ordered using training
correlation only. Spearman and same-minute return correlations are descriptive.
One week and a stationary permutation null cannot establish causality, stable
profitability or robustness across market regimes.

The spot accountant treats the declared fee plus execution allowance as one
additive notional cost. Independent canonical replays check selected P&L. The
canonical engine has no ten-minute enum: its accounting-only cross-check uses
an artificial one-minute clock without changing any price or target; the run
retains the original ten-minute timestamps and publishes no annualized metrics
from that check. Grid/DCA skip that unsupported cadence explicitly. Volty uses
synthetic 1x long/short accounts with declared 0.1bps/hour carry and does not
claim actual funding, liquidation or venue fills.

The first run's 1,638 global/rolling cycle tests and 1,999 null replicates give
a minimum attainable first Holm p-value of 0.819. Cycle significance is therefore
resolution-limited and inconclusive. At least 32,759 replicates would be needed
even to make 0.05 attainable for this family; the current run makes no claim
that the absence of a rejection disproves a cycle.

Missing primary minutes refuse the simulation while preserving acquisition.
Missing benchmark minutes invalidate affected correlation observations. No
prices, volumes or missing bars are filled. Coinbase's inclusive boundary
responses are filtered into fixed half-open windows of 299 minutes; pages
remain under its 300-candle cap. Raw responses and normalized rows are checked
against one another on reuse. Retryable reads have three bounded attempts;
malformed data, conflicting duplicates, redirects and nonretryable errors
refuse the run. No credentials are needed.

Binance pages use 1,000-minute half-open windows and validate both the minute
open and its exact close timestamp. All normalized candles reproduce from
the archived provider bytes. The first Coinbase attempt omitted the same two
minutes for ETH and BTC, confirmed by narrow re-requests. It is preserved under
`/Users/mitch/.local/state/weekly-coin-2571/coinbase-incomplete-attempt`.
The final run acquired its complete ETH/BTC/ZEC panel separately from Binance.
It did not splice the missing Coinbase minutes with another venue.

The existing Coinbase acquisition code and its public candle contract guided
the downloader. Context7 was unavailable because its monthly quota was reached;
Orbit discovery returned HTTP 403, and Postman account search was unavailable
because the CLI was signed out. Contract checks therefore reuse the repository's
named Coinbase row mapping and real public-market requests. These documentation
lookup failures do not certify a market-data response.

The report is generated from its bound summary. Offline verification checks
artifact hashes, raw-page normalization, result counts and report reproduction.
The PNG compares rebased prices and final-window feature correlations. Full
numeric rows and compressed source pages remain available in the complete archive.

An input ledger freezes all snapshot hashes before numerical data is loaded.
Every cache proof and finalization checks that same ledger. Corrections require
a new run. The trigger adapter also preserves full causal prefixes for the
strategy's absolute entry indices, fixing a crash beyond its former 6,512-bar
indicator limit without changing trigger rules.
