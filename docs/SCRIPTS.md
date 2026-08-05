# SCRIPTS.md — every runnable entry point

A single index of everything in this repository you can run, what it does, and the flags it
actually accepts. Flags below were read from each script's own `--help` rather than from memory; if
one disagrees with reality, the script is authoritative and this file is the bug.

**Run everything from the repository root** unless a section says otherwise. Python is 3.13;
dependencies are in `backtester/requirements.txt` and deliberately minimal. The JavaScript side has
**zero runtime dependencies** and no build step.

> **Safety, before anything else.** The extension can place real orders. It installs **disarmed** and
> `DEFAULT_CONFIG.mode` is `dry-run`; nothing in this document arms it, and no command here should be
> assumed safe to point at a funded account. The backtester and `research/` are simulation only. See
> `docs/SECURITY.md` and the extension's README "Verification status" before going near live mode.

## Contents

1. [Verification gate — run this before claiming anything works](#1-verification-gate)
2. [Fetching data](#2-fetching-data)
3. [Backtesting a single strategy](#3-backtesting-a-single-strategy)
4. [Research sweeps](#4-research-sweeps)
5. [The 1-minute pipeline](#5-the-1-minute-pipeline)
6. [Verifying the documents' numbers](#6-verifying-the-documents-numbers)
7. [The extension](#7-the-extension)
8. [SolTUI — the TUI and menu-bar app](#8-soltui)
9. [The vendored skill](#9-the-vendored-skill)
10. [Where output lands](#10-where-output-lands)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Verification gate

Run all four before claiming a change works. This is the list from `CLAUDE.md`, and the counts move
as tests are added.

```bash
python3 -m unittest discover -s backtester/tests -t .    # backtester + research
cd extension && npm test                                 # extension
node tools/dryrun.js --ticks 8 --osc 6 --offline 100     # a round trip must close positive
node tools/verify-endpoints.js                           # live Jupiter reachability (network)
```

Plus, for the TUI:

```bash
python3 -m unittest discover -s soltui/tests -t .
```

**Loading the extension unpacked cannot be automated** — `chrome://extensions` needs a human. Do not
claim it as verified; the headless dry run is the integration gate instead.

---

## 2. Fetching data

The engine never touches the network. Fetching is a separate, explicit step that writes a local CSV
cache under `data/` (gitignored and regenerable).

### One asset, one interval

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
```

| Flag | Meaning |
| --- | --- |
| `--asset` | base asset, e.g. `SOL` |
| `--quote` | quote currency, default `USD` |
| `--start`, `--end` | date bounds; `--end` is inclusive and defaults to today |
| `--interval` | `1m`, `5m`, `15m`, `1h`, `6h`, `1d` |
| `--out` | output CSV path |
| `--allow-gaps` | accept a series with holes instead of refusing |

### A whole universe, honestly

```bash
python3 -m backtester.core.universe --plan-only            # see the split first
python3 -m backtester.core.universe --interval 1d --start 2021-01-01
```

| Flag | Meaning |
| --- | --- |
| `--assets` | comma-separated; defaults to the tradeable universe (top-10 non-pegged minus `EXCLUDED`) |
| `--plan-only` | print what would be fetched and stop |
| `--refetch` | ignore existing cache |
| `--allow-partial` | **proceed even though some assets are unavailable** |
| `--allow-gaps`, `--out-dir`, `--quote`, `--start`, `--end`, `--interval` | as above |

**`--allow-partial` is the flag to understand.** Coinbase does not list every asset in the universe —
TRX and RAIN are absent entirely. Without this flag the fetcher **refuses** rather than writing eight
files under a ten-asset name, because every cross-sectional statistic computed on the smaller set is
then silently survivorship-filtered by listing venue. The refusal is the feature.

### Accumulating a series that cannot be fetched retroactively

```bash
python3 -m backtester.core.archive_price --mint JLP --dry-run
python3 -m backtester.core.archive_price --mint JLP
```

Appends **one** spot price per invocation. It cannot recover the past — schedule it (cron/launchd) if
you want a usable series. `--mint` accepts `JLP`, `JUP`, `SOL` or a raw mint address.

---

## 3. Backtesting a single strategy

```bash
python3 -m backtester.cli --asset SOL --strategy all --split 0.7 --out results/
```

Key flags: `--strategy`, `--interval`, `--mode {spot,perp}`, `--leverage`, `--fee-bps`,
`--slippage-bps`, `--fill-delay`, `--split`, `--allow-short`, `--capital`, `--data`, `--synthetic N`,
`--allow-gaps`, `--no-charts`, `--out`, `--seed`, `--risk-free-rate`, `--rebalance-threshold`.

**`--split` is retained for contrast, not as the primary protocol.** `research/RANKED_LISTS.md`
finding 1 documents that this dataset's 70/30 split ends on the highest close in the entire series,
which makes the out-of-sample leg structurally doomed. Use CPCV (§4) for anything you intend to
believe.

### The ladder grid

```bash
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 --notional-per-rung 12
```

Required: `--lower`, `--upper`. Then `--rungs`, `--notional-per-rung`, `--spacing {arith,geom}`,
`--deadband-bps`, `--min-order-usd`, `--carry-bps-per-hour`, plus the usual data and cost flags.

`core/gridsim.py` is a port of `extension/src/core/grid.js`. **A change to either one's economics
needs the matching change in the other**, or the backtest becomes a confident wrong number about the
live strategy.

### Pairs / relative value

```bash
python3 -m backtester.paircli --asset SOL --peer BTC --interval 1d --json
```

Flags: `--fit-window`, `--entry-z`, `--exit-z`, `--stop-z`, `--adf-max-p`,
`--no-cointegration-gate`, `--split`, `--data-dir`, `--json`.

`--no-cointegration-gate` disables the test that makes the spread meaningful. Trading a spread that
is not cointegrated is trading a random walk difference; the gate exists for a reason.

---

## 4. Research sweeps

All write to `research/results/`. Run them in roughly this order — each answers a question raised by
the previous one.

### 4.1 Walk-forward sweep (retained as contrast)

```bash
python3 research/sweep.py                                   # all stages, all horizons
python3 research/sweep.py --stage singles --horizon long
python3 research/sweep.py --stage triples --triple-top 8
```

### 4.2 CPCV — the primary protocol

```bash
python3 research/cpcv_sweep.py                                        # singles, all horizons
python3 research/cpcv_sweep.py --stage pairs --stage triples
python3 research/cpcv_sweep.py --horizon long --groups 8 --k 2
python3 research/cpcv_sweep.py --quiet                                # suppress the legend
```

Combinatorial Purged Cross-Validation: `C(N,k)` regime-mixed out-of-sample paths instead of one
split, plus **PBO** (probability of backtest overfitting). The output explains itself — `--quiet`
turns that off if you are parsing it.

**How to read PBO:** `0.500` is pure noise, `0.000` is a perfectly ordered signal, and **above 0.500
means in-sample rank is anti-informative** — worse than useless for selection. The daily horizons
here sit at 0.700.

### 4.3 Parameter perturbation

```bash
python3 research/perturb.py --all-singles --horizon long
python3 research/perturb.py --pair vol_regime zscore --mode all
python3 research/perturb.py --single obv_trend --pct 0.10
python3 research/perturb.py --triple ma_crossover sma_regime zscore --no-geometry
```

Flags: `--horizon`, `--pair A B`, `--triple A B C`, `--single NAME`, `--all-singles`,
`--mode {all,any,vote,mean}`, `--pct`, `--groups`, `--k`, `--no-geometry`, `--out`.

Perturbs one parameter at a time by `±--pct`. **Deliberately not a joint grid** — a joint sweep *is* a
parameter search, and would reintroduce the selection bias the whole protocol exists to measure.

### 4.4 Block-count geometry

```bash
python3 research/geometry.py --horizon long --blocks 6 12 --k 2
```

Re-ranks every strategy at each block count in `[LO, HI]` and reports whether the *ranking* survives.
Because nobody can justify 8 blocks over 9, a ranking that moves with the block count is reporting
how the series was sliced. **At the long horizon it does**: mean pairwise Spearman +0.566, the median
strategy moving 12 of 25 places, six different strategies holding first place across seven
geometries. Only strategies evaluable at *every* block count are compared, and the dropped names are
reported with the reason.

---

## 5. The 1-minute pipeline

Separate from §2 and §4 because the scale changes the engineering: ~2.6M bars per asset, ~1GB of CSV,
and a fetch measured in hours.

### 5.1 Fetch

```bash
python3 -m backtester.core.fetch_minutes --asset BTC --years 5
python3 -m backtester.core.fetch_minutes --all --years 5 --workers 6
python3 -m backtester.core.fetch_minutes --all --coverage-only      # measure, fetch nothing
python3 -m backtester.core.fetch_minutes --asset BTC --max-windows 50   # pilot
```

| Flag | Meaning |
| --- | --- |
| `--asset` | repeatable |
| `--all` | BTC, ETH, SOL, DOGE, ZEC, XRP, BNB, HYPE — the Coinbase-listed subset |
| `--years` | default 5 |
| `--workers` | concurrent requests, default 6; a **shared** limiter still caps aggregate throughput at 8/s |
| `--max-windows` | stop after N windows per asset, for piloting |
| `--no-resume` | refetch everything, ignoring the progress sidecar |
| `--coverage-only` | re-measure what is on disk |

**It is resumable — kill it and re-run it.** Each completed 300-minute window is appended immediately
and its start recorded in `data/<ASSET>_1m.progress.json`.

**Read the coverage table, not just the bar count.** Two different absences look identical in a bar
count and the table separates them:

- **`short by`** — missing *calendar*. The venue has no more history. XRP starts at its 2023
  relisting; BNB has ~287 days; HYPE ~181.
- **`complete`** — missing *minutes inside* the calendar it does cover. **ZEC covers the full five
  years and is only 60.2% complete** — it does not trade every minute. Every lookback in the engine
  counts *bars*, so a 200-bar average on ZEC spans far more wall-clock time than 200 minutes, and
  nothing downstream can tell.

Coverage is recorded in `research/results/minute_coverage.json`, which is tracked. The CSVs are not.

### 5.2 Preliminary sweep

```bash
python3 research/minute_sweep.py                                  # 500k bars per asset
python3 research/minute_sweep.py --common-window --tag common     # like-for-like
python3 research/minute_sweep.py --all-bars                       # full history; hours
python3 research/minute_sweep.py --param-scale 60                 # wall-clock params; slow
python3 research/minute_sweep.py --asset BTC --strategy macd --bars 50000
```

| Flag | Meaning |
| --- | --- |
| `--asset`, `--strategy` | repeatable filters |
| `--bars` | most recent bars per asset, default 500,000 (~347 days) |
| `--all-bars` | every cached bar |
| `--common-window` | intersect all assets' calendars so cells are comparable |
| `--param-scale` | multiply bar-count parameters (60 preserves the hourly wall-clock window) |
| `--workers` | default `min(6, cpu-2)` |
| `--tag` | suffix for the output filenames |

**Three things to know before reading its output.**

**It is preliminary, and the word is load-bearing.** One pass per cell — no CPCV, no PBO, no split.
This repo's own finding 1c measures in-sample rank as anti-informative, so a good number here is a
reason to spend a real protocol on that cell, not evidence.

**`--common-window` vs the default is a real choice.** By default each asset uses its own recent
bars, so spans differ and **cross-asset rows are not like-for-like**. `--common-window` intersects the
calendars, which is comparable but bounded by the shortest history (~181 days, HYPE).

**Parameters are bar counts.** `ma_crossover(fast=12, slow=48)` was tuned on hourly bars; at 1m the
same numbers mean 12 and 48 *minutes* — a different strategy, not the same one at finer resolution.
`--param-scale 60` restores the wall-clock window and only scales genuine bar-count keys, never a
threshold like `num_std`. It is expensive: `macd` went from 0.1s to 29.6s on 20k bars.

**Expect costs to dominate.** Measured on 100k bars of BTC, 22 of 25 strategies lost 79–100% of
capital with $7,800–$9,900 of fees against $10,000. Every row reports gross beside net for that
reason — if gross is near zero and net is −90%, the diagnosis is "no edge big enough to pay the
spread", which is different from a broken signal.

---

## 6. Verifying the documents' numbers

```bash
python3 research/verify_numbers.py        # exit 0 iff every figure matches its source run
```

Extracts every figure it can recognise from `research/RANKED_LISTS.md` and `research/STRATEGIES.md`
and checks each against the run that produced it — the walk-forward CSV, the CPCV results, the
perturbation CSVs — and for the derived block-count figures **recomputes** them from the raw
per-block medians, because no CSV contains a "median across geometries" to look up.

**It is deliberately brittle, and that is the point.** `EXPECTED_FIGURES` records how many figures
each document carries **per pattern family**, and a mismatch in either direction fails the run:

- **Fewer** → a table's format drifted and figures went unchecked.
- **More** → figures were added; raise the constant in the same commit, after reading the new count.

Never lower a count to make a red run green — that is the same act as deleting the evidence. If it
fails with `PREFLIGHT FAIL`, the results are stale or missing; regenerate them with the command the
message prints rather than editing the document.

---

## 7. The extension

```bash
cd extension
npm test                                                # no build step, zero deps
node tools/cli.js                                       # list every available command
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # headless tick loop
node tools/verify-endpoints.js                          # live Jupiter reachability
node tools/api-server.js                                # local HTTP surface
node tools/deps.js                                      # dependency report
```

`package.json` scripts: `test`, `smt` (→ `tools/cli.js`), `api`, `verify:endpoints`, `dryrun`.

Configuration example:

```bash
node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7 --notionalPerRungUsd 12
```

**Every action lives in `src/core/commands.js`.** The CLI, the message handler and the HTTP route are
three surfaces over one registry — do not add logic to a surface. `test/surfaces.test.js` will fail,
and correctly so.

**No live order has ever been placed from this codebase.** The Trigger order-list response envelope
is guessed and fee attribution is unconfirmed. Read the extension README's "Verification status"
before extending it, and do not present any of it as working.

---

## 8. SolTUI

A Textual TUI plus a rumps menu-bar app. Dry-run only: `MODES = ("dry-run",)`, and there is **no order
path in `soltui/` at all**.

```bash
python3 -m soltui.tui                     # the TUI
python3 -m soltui.app                     # the menu-bar app (foreground)
python3 -m unittest discover -s soltui/tests -t .
```

### Install as a login item

```bash
soltui/soltui-service build        # build the .app bundle
soltui/soltui-service install      # copy the bundle to ~/Applications, write the LaunchAgent
soltui/soltui-service status
soltui/soltui-service start
soltui/soltui-service stop
soltui/soltui-service uninstall
```

Full subcommand list, from its own usage: `{build, install, start, status, stop, uninstall}`.

Edit **the script**, not the generated plist — `install` overwrites the plist every time.

### Build the app bundle and the icon

```bash
python3 soltui/setup_app.py py2app -A     # alias build (recommended)
python3 soltui/make_icon.py --preview     # regenerate the .icns, plus a 512px PNG to eyeball
```

**A py2app "Launch error" dialog keeps the process alive**, so a liveness check is not evidence the
app started. The stderr log is the real signal.

---

## 9. The vendored skill

`skills/trading-and-investing/` is a **copy** of the live skill at
`~/.claude/skills/trading-and-investing/`. Editing the copy changes nothing at runtime.

```bash
rsync -a --delete ~/.claude/skills/trading-and-investing/ skills/trading-and-investing/
```

If the two diverge, the live one wins. See `skills/README.md`.

---

## 10. Where output lands

| Path | Tracked? | Contents |
| --- | --- | --- |
| `data/` | **no** | fetched OHLCV CSVs and 1m progress sidecars; regenerable |
| `research/results/` | **yes** | sweep CSVs, text reports, coverage manifest — the evidence `verify_numbers.py` checks |
| `research/results/.slices/` | **no** | 1m array cache, rebuilt on demand |
| `results/` | **no** | `backtester.cli --out` default |

**`research/results/` is tracked on purpose.** It was gitignored once, which meant
`verify_numbers.py` had nothing to check against and reported a pass over 454 failing checks. The
ignore pattern is anchored (`/results/`) so it cannot match `research/results/` at any depth again.

---

## 11. Troubleshooting

**`verify_numbers.py` says `PREFLIGHT FAIL`.** The results are stale or partial. Regenerate with the
exact command in the message. Do not edit the document to match.

**A figure count mismatch.** See §6 — update `EXPECTED_FIGURES` deliberately, in the same commit as
the figure change.

**`fetch_minutes` is slow.** Expected throughput is ~6–7 windows/s against a shared 8/s limit. The
endpoint answers in ~0.20s median but ~15% of connections stall, which is why `REQUEST_TIMEOUT` is 3s
— raising it makes throughput *worse*, not better.

**`fetch_minutes` reports `PARTIAL`.** Some windows were not attempted. Re-run the same command; it
resumes.

**`minute_sweep.py` dies with `BrokenProcessPool`.** Out of memory. Lower `--workers` or `--bars`.
Slices are prepared once in the parent precisely to bound this; if it still happens the slice itself
is too large for your machine.

**A strategy takes minutes per cell at 1m.** Indicator cost is proportional to the window, so
`--param-scale 60` multiplies it. `rsi` extrapolates to ~1.8h per asset on a full 2.6M-bar series.
Bound it with `--bars`.

**`node tools/verify-endpoints.js` fails.** It needs network. A failure is not a code fault — do not
substitute synthetic data for a real-data run.

---

## Related

- `CLAUDE.md` — the non-negotiables per component. Read before changing code.
- `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/OPERATIONS.md`, `docs/SECURITY.md`, `docs/TESTING.md`
- `backtester/README.md`, `extension/README.md` — component detail and verification status
- `research/RANKED_LISTS.md` — the findings the sweeps produced, and how to read the tables
