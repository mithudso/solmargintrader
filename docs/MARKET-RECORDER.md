# Market recorder

Version: 1.1.0. Tools: `extension/tools/market-recorder.mjs` and `extension/tools/market-recorder-fill.mjs`.

A long-running recorder for every Jupiter 1000x and Perps market, with Coinbase's order book and trades for the same coins beside them. It writes one folder per coin under `/Volumes/dasdata/CoinTradingData`.

It reads public data only. It holds no wallet and no key, and it sends nothing to a venue except the two stream subscriptions. It places no order and has no code that could.

## What is recorded

| Folder under each coin | Source | Content | How often |
|---|---|---|---|
| `oracle/` | Jupiter Pyth oracle stream | Price ticks, the price the 1000x product opens and closes against | About two a second |
| `1000x-market/` | Jupiter 1000x catalog | Open interest long and short, 24 hour volume, open or closed | Read every 15 s, written when it changed |
| `perps-book/` | Jupiter Perps order-book markets | Best bid and ask, mark, index, last trade, open interest, 24 hour volume | Read every 2 s, written when it changed |
| `perps-funding/` | Jupiter Perps order-book markets | Funding rate and its next collection time | Read every 60 s, written when it changed |
| `perps-pool/` | Jupiter Perps pool (SOL, ETH, BTC) | Open fee, borrow rates, utilization, available liquidity | Read every 30 s, written when it changed |
| `coinbase-book/` | Coinbase Exchange `level2_batch` | Best bid and ask with their sizes | A row each time one of them changes |
| `coinbase-trades/` | Coinbase Exchange `matches` | Every trade: price, size, side | Every trade |
| `coinbase-depth/` | Coinbase book kept in memory | Size resting within 5 and 25 basis points of the middle, each side | Once a second, written when it changed |

Which coins get which folders depends on what each venue lists. The lists are read from the venues while the recorder runs, so a new market is picked up without a restart.

| Coins (2026-11-28) | Oracle and 1000x | Perps book and funding | Perps pool | Coinbase |
|---|---|---|---|---|
| BTC, ETH, SOL | Yes | Yes | Yes | Yes |
| ZEC, HYPE | Yes | Yes | | Yes |
| BNB, NEAR | | Yes | | Yes |
| ANT, JUP, SKHYNIX, SNDK, SPCX | | Yes | | |
| XAU, WTI | Yes (oracle only while the market is open) | | | |

Jupiter's feed has no order book and no trades of its own for the 1000x and oracle-priced Perps markets: those are priced by an oracle. That is why Coinbase is recorded beside it. In [the scalp study](../research/papers/SCALP-1S-STUDY.md) Coinbase's book moved about a second before the oracle did, and most of that lead is gone by the time an order could fill.

## Files

```
/Volumes/dasdata/CoinTradingData/
  BTC/oracle/2026-11-28/BTC-oracle-20261128T10.jsonl.gz
  BTC/coinbase-book/2026-11-28/BTC-coinbase-book-20261128T10.jsonl.gz
  ...
  _recorder/status.json     state of the run, rewritten every ten seconds
  _recorder/events.jsonl    starts, stops, reconnects, failed reads and compressions, faults
  _recorder/lock            the process that is recording
  _recorder/fills.jsonl     rows added from the second recording, per file
  _recorder/compare.jsonl   how the two recordings compared, per hour
```

- One file per coin, stream and UTC hour. Each line is one JSON object.
- The hour in progress is a plain `.jsonl` file. When the hour ends the file is gzipped and the plain copy removed, unless `--no-gzip` is set.
- A file can hold more than one gzip member (after a restart inside an hour). `gzip`, `zcat`, Python's `gzip` module and DuckDB all read that as one file.
- A polled stream writes a row when something changed and one at the start of every hour, so every file can be read on its own.
- A crash can leave one cut line mid-file; skip any line that is not valid JSON.

### Rows

`r` is always the recorder's receive time in milliseconds. A venue's own time is kept beside it under its own key. A figure the venue did not send is `null`, never zero, and so is a Perps book price of zero or less. A row with `h` was recorded by the machine named there and added later to fill a gap; its `r` is that machine's receive time.

| Stream | Fields |
|---|---|
| `oracle` | `a` coin, `p` price, `e` oracle time (ms), `r` |
| `1000x-market` | `closed`, `closeOnly`, `longOi`, `shortOi`, `volume24h`, `totalVolume`, `r` |
| `perps-book` | `bid`, `ask`, `mid`, `mark`, `index`, `last`, `openInterest`, `openInterestBase`, `volume24h`, `maxLeverage`, `status`, `venueTime` (s), `updatedMs`, `r` |
| `perps-funding` | `rateBps1h`, `fundingRate`, `predictedFundingRate`, `intervalSeconds`, `nextCollection` (s), `venueTime` (s), `r` |
| `perps-pool` | `openFeePercent`, `maxPriceImpactFeePercent`, `longBorrowRatePercent`, `shortBorrowRatePercent`, `longUtilizationPercent`, `shortUtilizationPercent`, `longAvailableLiquidity`, `shortAvailableLiquidity`, `r` |
| `coinbase-book` | `bid`, `ask`, `bidSize`, `askSize`, `t` Coinbase time (ms, `null` when the message carried none), `r` |
| `coinbase-trades` | `price`, `size`, `side` (the maker's side, as Coinbase reports it), `tradeId`, `t`, `r` |
| `coinbase-depth` | `bid`, `ask`, `bid5`, `ask5`, `bid25`, `ask25`, `r` |

The `oracle` rows have the shape the scalp study reads, so a file can be passed to it directly:

```sh
python -m research.scalp_1s_coins --ticks /Volumes/dasdata/CoinTradingData/SOL/oracle/2026-11-28/SOL-oracle-20261128T10.jsonl.gz --out /tmp/sol.json
```

## Running it

```sh
cd /Users/mitch/dev/solmargintrader/extension
node tools/market-recorder.mjs --out /Volumes/dasdata/CoinTradingData
node tools/market-recorder.mjs --help
```

It needs Node 22 or later.

| Option | Default | Meaning |
|---|---|---|
| `--out` | `/Volumes/dasdata/CoinTradingData` | Absolute; must already exist |
| `--minutes` | `0` | Minutes to record; `0` until stopped |
| `--book-every`, `--catalog-every`, `--funding-every`, `--pool-every` | `2`, `15`, `60`, `30` | Seconds between reads, 1 to 3600 |
| `--no-gzip` | off | Leave finished hour files plain |
| `--keep-hours` | off | 1 to 24. Makes the folder a short-lived copy: compressed hours that ended longer ago are deleted. See [a second recording that fills gaps](#a-second-recording-that-fills-gaps) |

### As a background service (macOS)

The recorder is built to be restarted by a supervisor. It exits when something is wrong that it cannot fix, and starts clean:

| Exit | Meaning |
|---|---|
| 0 | Stopped on request, or the `--minutes` limit was reached |
| 1 | The disk stopped taking writes or went away, the start failed, a stop overran five seconds, or a fault nobody caught |
| 2 | Bad options, the output folder is missing, Node is too old, or `--keep-hours` does not match the folder (see below) |
| 3 | Another recorder is already writing to the folder |
| killed | Its own watchdog ended it because the process had frozen (a hung network disk) |

A launchd agent keeps it running across crashes, and starts it again at login after a restart. The agent file is `~/Library/LaunchAgents/com.solmargintrader.market-recorder.plist`; `KeepAlive` restarts the recorder whenever it exits, and `ThrottleInterval` keeps that to once every 30 seconds while the disk is away.

```sh
launchctl print gui/$(id -u)/com.solmargintrader.market-recorder | head -20   # is it running
launchctl bootout gui/$(id -u)/com.solmargintrader.market-recorder             # stop it
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.solmargintrader.market-recorder.plist   # start it
cat /Volumes/dasdata/CoinTradingData/_recorder/status.json                     # what it is doing
```

### What it does when things go wrong

- **The disk goes away.** Within ten seconds the recorder notices the folder is gone, or is no longer the same disk, and exits. It never creates the folder again and never writes anywhere else. The supervisor starts it again every 30 seconds until the disk is back.
- **The disk hangs.** A frozen network disk can block the process without ending it. A watchdog on its own thread ends the process after a minute without a heartbeat. A machine waking from sleep is not mistaken for that.
- **The disk is slow.** Rows wait in memory. Past 64 MB waiting, the recorder exits, before memory runs out.
- **The oracle or Coinbase stream drops.** It is reconnected, one attempt at a time, waiting from half a second up to a minute between attempts. The waits start over only after the stream has stayed up for 30 seconds. A stream silent for 20 seconds is replaced without a wait. The Coinbase book is rebuilt from a new snapshot each time.
- **One market's read fails.** The others are still read; the failed one waits for the next regular read. A read that fails as a whole is tried again within five seconds, then more slowly, up to once a minute. `events.jsonl` notes the first failure in a row and every twentieth.
- **A crash in the middle of compressing an hour.** The next start finishes the job for every folder, and an hourly sweep does the same for the last two days. An hour is never lost and never written twice.
- **A second copy is started.** It is refused (exit 3). A lock left behind by a crash or a restart of the machine is recognized as stale and replaced; `events.jsonl` notes it. Another machine's lock counts while its `status.json` is under a minute old.

While this machine restarts, sleeps or has no network, it records nothing, and `events.jsonl` shows when the streams came back. A second recording on another machine fills such gaps where it can.

## A second recording that fills gaps

A second copy of the recorder runs on another machine (the 5080 workstation) and keeps only its last three hours. Every half hour a job on this Mac copies that folder here and does two things with it.

**It fills gaps.** A stretch in which the archive has no row at all from a venue for more than 15 seconds is a stretch in which the archive was not recording that venue. A venue is every Jupiter stream of every coin, or every Coinbase one. Rows the second machine recorded inside such a stretch are added to the archive's hour files, in time order. A healthy recorder is never silent that long: on 2026-11-28 the longest silence was under five seconds for Jupiter and half a second for Coinbase. Outside those stretches nothing is added, so the archive stays what one listener saw.

- A row from the second machine carries `h`, that machine's name. Its `r` is that machine's receive time.
- A tick or a trade the archive already has is not added again. Oracle ticks are matched by `e`, trades by `tradeId`.
- An hour's file is rewritten as a whole beside the old one, checked to hold every old line in its old order, and put in its place in one step. If the recorder changed the file meanwhile, it is left alone and tried again on the next run.
- Only finished hours are looked at, ten minutes after they end, once each. `_recorder/fills.jsonl` lists what was added to which file.

It cannot fill a stretch both machines missed, or one older than the second machine still holds when the job next runs.

**It compares.** Where both machines were recording, the job counts the oracle ticks and Coinbase trades both saw, those only one saw, those whose values differ, and how much later the second machine received them. One row per hour goes to `_recorder/compare.jsonl`.

```sh
# On the second machine: a short-lived copy.
node tools/market-recorder.mjs --out /home/mitch/CoinTradingStandby --keep-hours 3
# On this Mac: copy it here, then fill and compare.
node tools/market-recorder-fill.mjs --from /Users/mitch/.local/state/solmargintrader/market-standby --pull 5080:CoinTradingStandby/
# Say what would be added, and write nothing.
node tools/market-recorder-fill.mjs --from /Users/mitch/.local/state/solmargintrader/market-standby --dry-run
```

`--keep-hours` is the only thing in the recorder that deletes, so it is fenced in:

- It starts only in a folder that holds no recording yet, which it marks with `_recorder/standby`, or in one it marked before. In a folder that already holds a recording it exits with 2.
- A marked folder does not start without `--keep-hours` (exit 2).
- It deletes compressed hour files of its own naming that ended more than that many hours ago, and day folders left empty. It never deletes a plain file, a file of another name, or anything in an unmarked folder.
- The fill job takes rows only from a marked folder and writes only into an unmarked one. Given the two the wrong way round, it exits with 2 and changes nothing.

The second machine needs only the recorder's three files (`tools/market-recorder.mjs` and the two in `tools/lib/`), which have no dependencies:

```sh
rsync -a --relative /Users/mitch/dev/solmargintrader/extension/./tools/market-recorder.mjs \
  /Users/mitch/dev/solmargintrader/extension/./tools/lib/market-recorder.mjs \
  /Users/mitch/dev/solmargintrader/extension/./tools/lib/market-recorder-run.mjs 5080:market-recorder/
```

| Where | Service | What it runs |
|---|---|---|
| 5080 | systemd user unit `market-recorder-standby.service` | The recorder with `--keep-hours 3`, restarted 30 seconds after any exit |
| This Mac | launchd agent `com.solmargintrader.market-recorder-fill` | The fill job every 30 minutes |

## Size

On 2026-11-28 the fourteen coins wrote about 13 kB a second before compression, roughly 1.1 GB a day, and about a tenth of that once the hour files are gzipped. A year is on the order of 40 GB.

## Why files and not a database

The recorder writes files because the capture has to outlast crashes and a disk that comes and goes: a file append needs no server and cannot be blocked by a schema, and a crash loses only rows still in memory. The files are the source of truth, and anything else can be rebuilt from them.

| Option | Good for | Why it is not the capture store here |
|---|---|---|
| **Hourly gzipped JSON lines** (what is used) | Appending forever; sequential replays, which is what every study in this repository does | |
| **Parquet with DuckDB** | Ad hoc SQL over months of ticks without a server, at a few times better compression | Parquet is written in batches, so it suits a nightly conversion of finished hours, not the live append |
| **MongoDB time series collection** | Dashboards and queries by coin and time from other tools; this repository already has a derived store in `mongo/` | A server that must be up for every tick, on a NAS that can drop out; it is a good second copy, loaded from the files |
| **QuestDB, ClickHouse, TimescaleDB** | Thousands of rows a second with SQL | More to run than under 100 rows a second needs |

The practical order is: record to files now, convert finished hours to Parquet when queries get slow, and load a MongoDB time series collection from the files if a dashboard or another tool needs one. DuckDB reads the files as they are:

```sql
SELECT a, count(*), min(p), max(p)
FROM read_json_auto('/Volumes/dasdata/CoinTradingData/*/oracle/2026-11-28/*.jsonl.gz')
GROUP BY a;
```

## Tests

`npm test` in `extension/` runs `test/market-recorder.test.js` and `test/market-recorder-fill.test.js`. The first covers the catalog and stream parsing, the Coinbase book against hand-built cases, file naming, and the recorder itself against a temporary folder with a scripted clock and network. Those cover hourly rotation, a clock that steps backwards, a restart inside an hour, a row cut off by a crash, every crash point of the compression, a failing market, reconnects and their waits, a missing folder, the lock and its stale cases, the backlog limit, running without compression, a sweep that meets a file still open or still closing, the short-lived copy and its safeguards, and the watchdog. The second covers which stretches count as gaps, which rows are taken, that an hour file is replaced only by a copy holding every old line, that a second run adds nothing, the comparison counts, and the refusals when folders are the wrong way round.

Not tested: weeks of running against the real venues and the real NAS. `status.json` and `events.jsonl` are how that is watched.
