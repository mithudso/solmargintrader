# Development

Setup, the commands you will actually use, and the environment each component needs.

## Prerequisites

| Need | Version | Why that one |
| --- | --- | --- |
| Python | 3.13 | The codebase uses `enum.StrEnum` and 3.13-era typing; CI pins 3.13 |
| Node | 22 | Ed25519 in WebCrypto and `node:test`'s current output both need a recent runtime; `.nvmrc` pins it |
| macOS | Any recent | Only for `soltui/` — the menu-bar app and launchd agent are macOS-only |

Everything else is stdlib. There is no build step anywhere in the repo.

## Setup

```bash
git clone <this repo> && cd solmargintrader

# Python side: the backtester's deps cover research/ too.
pip install -r backtester/requirements.txt

# Extension: nothing to install. Zero runtime and zero dev dependencies, on purpose.
cd extension && npm test && cd ..

# soltui, only if you want the menu-bar app:
pip install -r soltui/requirements.txt
```

`backtester/requirements.txt` deliberately excludes `pyarrow`, `requests` and `pytest`.
Tests use `unittest`; HTTP uses `urllib`. Do not add a dependency to solve something the
stdlib already covers.

## Commands

### Backtester

```bash
# Fetch once (the only network step), then simulate offline forever.
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
python3 -m backtester.cli --asset SOL --strategy all --split 0.7 --out results/

python3 -m backtester.gridcli --help    # ladder grid: its own bar loop, its own entry point
python3 -m backtester.paircli --help    # pairs / cointegration
```

### Research

```bash
# What every strategy, signal and indicator says about the last cached bar.
python3 research/decide.py --asset SOL --interval 1d
python3 research/decide.py --data data/ZEC_1d.csv --json

python3 research/sweep.py            # parameter sweeps
python3 research/cpcv_sweep.py       # CPCV, with the interpretation guard
python3 research/verify_numbers.py   # re-derives every figure quoted in the research docs
```

`verify_numbers.py` exiting 0 is the gate on research prose. Run it after editing any
document that quotes a number.

### Extension

```bash
cd extension
npm test                                              # 114 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # the integration gate
node tools/cli.js                                     # lists every command in the registry
node tools/api-server.js                              # local HTTP surface
node tools/verify-endpoints.js                        # live Jupiter reachability
```

Load it in Chrome: `chrome://extensions` → Developer mode → **Load unpacked** → select
`extension/`. It loads **disarmed, in dry-run**. That cannot be automated, so the headless
dry run is the integration gate instead — never claim the unpacked load as verified.

### soltui

```bash
python3 soltui/soltui-service status   # bundle / agent / flag / launchd state
python3 soltui/soltui-service start    # also starts at login
python3 soltui/soltui-service stop     # removes the flag file
python3 soltui/soltui-service build    # rebuild after moving the repo
```

The **flag file is the real off switch**, not the menu-bar Quit item: `KeepAlive`
necessarily overrides Quit, so stopping it means removing
`~/Library/Application Support/soltui/supervise.enabled`. Read `soltui/README.md` before
rebuilding — the py2app traps there have already been paid for once.

## Verification

Run all of these before claiming a change works:

```bash
python3 -m unittest discover -s backtester/tests -t .   # 454 tests
python3 -m unittest discover -s soltui/tests -t .       # 95 tests (~70s)
cd extension && npm test                                # 114 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must close POSITIVE
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
```

The oscillating dry run is the one that matters most: it is the only check that closes a
round trip, so it is the only one that can catch a zero-spread regression.

## Environment variables

Only `extension/tools/` reads the environment. The backtester, research and soltui
components read none.

| Variable | Read by | Purpose |
| --- | --- | --- |
| `JUPITER_API_KEY` | `tools/verify-endpoints.js:18` | Live reachability check. The extension itself does **not** read this — its key lives in `chrome.storage.local` |
| `SMT_API_PORT` | `tools/api-server.js:211` | Port for the local HTTP surface |
| `SMT_API_TOKEN` | `tools/api-server.js:213,228` | Bearer token the HTTP surface requires |
| `SMT_PASSPHRASE` | `tools/api-server.js:220` | Unseals the session-key vault for that surface |

Put real values in a local `.env` — `.gitignore` already covers `.env` and `.env.*` while
un-ignoring `.env.example`. Never commit one, and never log a value; see
`docs/logging.md`.

## Data

`data/` is a regenerable cache and is gitignored, so a fresh clone has none. Refetch with
`backtester.core.fetch`. Two shapes live there and they are not interchangeable:

- `<ASSET>_<interval>.csv` — OHLCV bars, `timestamp,open,high,low,close,volume`.
- `JLP_spot.csv` — a one-row Jupiter price snapshot from `core/archive_price.py`, with
  entirely different columns. Tools that expect bars must refuse it, and they do.

Coinbase is the fetch source because Binance is geo-blocked from here; mind its non-OHLCV
row ordering if you touch the fetch path.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `no cached data at data/SOL_1d.csv` | Fresh clone, gitignored cache. Run the fetch command |
| `N gap(s) larger than one 1h bar` | The cache has holes. Refetch, or pass `--allow-gaps` to accept it knowingly |
| `data is spaced as 1h bars but --interval says 1d` | `research/decide.py` refusing a mismatch that would corrupt its staleness and volatility figures. Use the interval it names |
| `missing required column(s)` | You pointed a bar tool at `JLP_spot.csv` |
| soltui not running after login | The flag file, not Quit. `python3 soltui/soltui-service status` |
| soltui bundle broken after moving the repo | It is an **alias** py2app build that references this checkout. `soltui-service build` |
| Dry run closes a round trip flat or negative | A real regression: the exit must rest one rung above the entry. See `expectedRoundTripUsd` |
