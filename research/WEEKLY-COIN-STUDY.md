# Repeat the ZEC candle studies for another coin

Version: 2.0.0

## USD markets and lists of native pairs

Run from `/Users/mitch/dev/solmargintrader` in a Python 3.13 environment with
the backtester dependencies. The legacy single-coin default is still Binance
ETH/USDT. **USDT is not USD.** To test the actual ETH/USD market, use:

```bash
cd /Users/mitch/dev/solmargintrader
python -m research.coin_week --coin ETH --quote USD --output /Users/mitch/dev/solmargintrader/research/eth-usd-study
```

`--quote USD` selects Coinbase unless `--venue` is explicitly supplied. The
old ETH/BTC and ETH/ZEC headings meant comparisons of ETH/USDT returns with
BTC/USDT and ZEC/USDT returns. They did not represent native cross-pair trades.
Version 2 labels market backtests and return comparisons separately.

To download and backtest every combination of a list, use either commas or
spaces:

```bash
python -m research.coin_week --coins ETH,BTC,ZEC --quote USD --output /Users/mitch/dev/solmargintrader/research/eth-btc-zec-usd-study
```

The list defaults to Coinbase/USD. It includes each unordered pair among the
coins **plus the selected cash quote**. ETH,BTC,ZEC with USD therefore requests
six combinations: ETH/USD, BTC/USD, ZEC/USD, ETH/BTC, ETH/ZEC and BTC/ZEC.
If only the reverse orientation is listed, the report names that real market
and its account currency. An inactive or absent product remains in the report
with its reason. No candles are manufactured by dividing separate USD highs
or lows. The current product catalogue is frozen; it is not a historical
listing reconstruction. The input list is bounded to twelve distinct assets
because every available pair runs the full catalogue.

For Binance/USDT markets instead, use `--coins ETH BTC ZEC --quote USDT`.
Every native market is downloaded once and copied byte-for-byte to its child
analysis. Reference-return comparisons use other available native markets
with the same quote. `--references` is for single-coin mode only. Quotes are
never spliced across venues, and native BTC-denominated returns are not added
to USD-denominated account results.

Batch mode and explicit Coinbase quote mode default to `--gap-policy longest`:
the longest real contiguous segment, with the earliest segment breaking ties,
must contain at least 1,440 minutes. The report prominently shows requested
and actual UTC dates and marks a **REDUCED WINDOW**. A reduced window is not a
complete-week backtest. Choose `--gap-policy strict` to require every requested
minute. Existing single-coin commands without the new quote flag retain their
strict behavior. Missing bars are never filled. An insufficient native market
is reported separately, and acquisition/analysis failures leave a partial
report and a nonzero exit status.

The parent report lists all requested combinations and links each completed
market report. Each detailed report names the native product, account quote,
costs, time splits, selected underlying strategy and resolved default/override
parameters. It defines all six filter/control variants. In particular,
`linear_control` means **the underlying strategy gated by a positive slope
from a 64-closed-bar log-price linear regression, frozen for 16 bars**. It is
not a standalone strategy named LINEAR. Harmonic/linear/persistence price
forecast comparisons are a separate cycle diagnostic.

Every market retains the complete ZEC transfer and its limitations described
below. Future-return correlations receive the within-market max-statistic
correction and then Bonferroni correction over **all planned combinations**,
including unavailable ones. Same-minute correlations remain descriptive;
cycle Holm corrections remain within-market and cannot support batch-wide
cycle significance claims. Candidate selection stays chronological and
validation-only. A native candle simulation is not an execution qualification.

Fetch/offline/resume/verify work for batches using the same CLI:

```bash
python -m research.coin_week --coins ETH BTC ZEC --quote USD --output /Users/mitch/dev/solmargintrader/research/eth-btc-zec-usd-study --phase fetch
python -m research.coin_week --output /Users/mitch/dev/solmargintrader/research/eth-btc-zec-usd-study --phase analyze
python -m research.coin_week --output /Users/mitch/dev/solmargintrader/research/eth-btc-zec-usd-study --resume
python -m research.coin_week --output /Users/mitch/dev/solmargintrader/research/eth-btc-zec-usd-study --phase verify
```

Use a new output directory for changed coins, quote, venue, source version or
options. Resume retains the frozen batch plan and verifies its exact input
hashes and each completed child. Completed v1 single-coin reports still verify
with their original report bytes.

The completed native-pair example, with all 1,707 templates for each usable
USD market, is `/Users/mitch/dev/solmargintrader/research/native-pairs-week-20261117/report.md`.
Its adjacent `artifacts.zip` preserves the complete 246-artifact batch and
manifest. The report explicitly lists its three completed markets, three
unavailable/insufficient combinations, reduced windows and correlation test
coverage. It does not claim a full-week simulation or a qualified trading edge.

## Original single-coin transfer and preserved v1 run

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

With the strict gap policy, missing primary minutes refuse the simulation while preserving acquisition.
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
