# mongo/ — the local research store

A read-mostly MongoDB copy of everything this repo has measured: price history,
strategies and their cards, the signal and indicator layers, per-bar readouts,
backtest runs, CPCV and sweep results, the coin write-ups, and the test-suite
results. ~29,000 documents in the `solmargintrader` database on `localhost:27017`.

The files on disk stay the source of truth. This is a derived store, which is why
the loader can drop and rebuild it without asking.

> Research and educational tooling, not financial advice. Every figure here is a
> mechanical measurement over cached history. Read `docs/known-issues.md` before
> treating any of it as current.

## Setup

```bash
pip install -r mongo/requirements.txt        # pymongo only
brew services start mongodb-community        # if it is not already listening

python3 mongo/schema.py --describe           # the layout, no server needed
python3 mongo/load.py --dry-run              # what would load, writes nothing
python3 mongo/load.py                        # ~35s
python3 mongo/load.py --run-tests            # ~2min, also records real suite results
```

Verify:

```bash
python3 -m unittest discover -s mongo/tests -t .          # 20 tests
mongosh solmargintrader mongo/queries/08-provenance-and-health.js
```

## The loader drops before it writes

Deliberate, and worth understanding before you run it twice. A **time series
collection accepts no unique index**, so there is no upsert key for a bar and no
database-level guard against loading the same series again. A naive second run
would double all 18,381 bars and every subsequent query would be quietly wrong —
no error, no warning, just numbers that are half right.

Dropping first makes "run it again" safe. `mongo/tests/test_load.py` asserts two
consecutive loads leave identical counts.

`--only bars,strategies` recreates just those collections and leaves the rest
alone.

## Collections

| Collection | Documents | Shape |
| --- | --- | --- |
| `bars` | 18,381 | **Time series.** `ts` + `series` meta `{asset, interval, source, frame_checksum}` |
| `spot_prices` | 1 | **Time series.** The JLP snapshot — not OHLCV, see below |
| `equity_points` | 7,500 | **Time series.** `ts` + `curve` meta `{run_id, strategy}` |
| `strategies` | 45 | One per strategy card, with live registry facts embedded for the 25 registered |
| `signals` | 15 | The stateless one-bar rules from `research/decide.py` |
| `indicators` | 20 | 16 reported rows + 4 explicitly skip-listed functions |
| `decisions` | 6 | One per readout, exactly as `decide.build_report()` emits it |
| `backtest_runs` | 1 | Manifest + per-strategy metrics |
| `trades` | 114 | One per fill |
| `experiments` | 25 | One per result file: kind, columns, object sidecar |
| `experiment_rows` | 2,736 | One per result row. `section` is `result` or `summary` |
| `documents` | 78 | Markdown: coin spokes, research prose, component docs |
| `test_results` | 3 | A suite count + outcome per commit, from a real run |

### Four design decisions you will run into

**Bars are a native time series collection.** Filter on `series.*` and a time
range; MongoDB maintains the meta+time index itself and there are no user indexes
to add. Provenance lives on the metaField, where it is stored once per bucket
rather than once per bar.

**`spot_prices` is separate, with one document.** `data/JLP_spot.csv` is a Jupiter
price snapshot with columns `timestamp,iso,mint,usd_price,source` — no OHLCV at
all. `research/decide.py` refuses to read it as bars, and merging the two here
would contradict the distinction the code enforces.

**Strategy cards keep their own vocabulary.** There is no `registered` boolean.
`registry_key` is a string for the 25 registered `Strategy` implementations and
`null` for the other 20 — but null does *not* mean unimplemented: the ladder grid
is `status: "implemented"` with no key because it is not a `Strategy` at all. Use
`status` (`measured` / `implemented` / `spec-only`) and `runner` for the rest.

**List-shaped sidecars became rows, not blobs.** `cpcv_pbo.json` and the
`geometry_*_k2.json` files hold a *list* — one PBO per horizon, or per block count.
Those load into `experiment_rows` with `section: "summary"`, because PBO by horizon
is the most queried number in the research set and burying it in an opaque field
would have made it unreachable without client-side parsing. The `$jsonSchema`
validator caught this during development, which is the argument for having one.

## Question → query

Every file below is runnable as-is and commented with which index serves each
query.

```bash
mongosh solmargintrader mongo/queries/01-coins-and-bars.js
```

| Question | File | Collections |
| --- | --- | --- |
| What price history exists, and how stale is it? | `01-coins-and-bars.js` | `bars`, `spot_prices` |
| 30-day return per coin; biggest single-day drops | `01-coins-and-bars.js` | `bars` |
| What strategies exist; which actually run | `02-strategies-and-cards.js` | `strategies` |
| What could I build next, and what is blocked on data? | `02-strategies-and-cards.js` | `strategies` |
| What does this signal actually compare? | `03-signals-and-indicators.js` | `signals`, `strategies` |
| Which indicators have no directional reading? | `03-signals-and-indicators.js` | `indicators` |
| What does every rule say about the last bar? | `04-decisions.js` | `decisions` |
| Where do strategy families disagree? | `04-decisions.js` | `decisions` |
| What did the backtest actually return, after costs? | `05-backtests.js` | `backtest_runs`, `equity_points`, `trades` |
| Max drawdown per curve; fills and fees | `05-backtests.js` | `equity_points`, `trades` |
| **Is this result overfit? (PBO)** | `06-experiments-and-pbo.js` | `experiment_rows` |
| Best Sharpe per strategy, with trade counts | `06-experiments-and-pbo.js` | `experiment_rows` |
| Does a result transfer across coins? | `06-experiments-and-pbo.js` | `experiment_rows` |
| Full-text search the write-ups | `07-documents-and-search.js` | `documents` |
| Which coins have a write-up but no data? | `07-documents-and-search.js` | `documents`, `bars` |
| Can I trust this store? Where did a number come from? | `08-provenance-and-health.js` | all |

**Start with `06` before `05`.** A Sharpe with a PBO of 0.9 beside it is not a
result; `research/cpcv_sweep.interpret()` exists precisely to stop that reading.

## From Python

```python
import sys; sys.path.insert(0, ".")
from mongo.schema import DB_NAME, connect

db = connect()[DB_NAME]

# Last 5 SOL daily closes.
for bar in db.bars.find(
    {"series.asset": "SOL", "series.interval": "1d"}, {"_id": 0, "ts": 1, "close": 1}
).sort("ts", -1).limit(5):
    print(bar)

# PBO by horizon — the honesty number.
for row in db.experiment_rows.aggregate([
    {"$match": {"section": "summary", "pbo": {"$ne": None}}},
    {"$group": {"_id": "$horizon", "worst": {"$max": "$pbo"}}},
    {"$sort": {"worst": -1}},
]):
    print(row)
```

## Provenance

Every document carries `source_path`, `source_sha256` and `loaded_at`; time series
measurements carry the first two on their metaField. Bar series additionally carry
`frame_checksum` from `backtester.core.data.checksum_frame` — the same identity a
backtest manifest and a `decide.py` readout print, so a row here can be tied to
the exact frame a reported number came from.

That is the point of the store rather than a nicety. A figure you cannot trace to
a file is not a figure, which is the same reason `RunManifest` exists.

## Files

| Path | What it does |
| --- | --- |
| `mongo/schema.py` | Collection specs, `$jsonSchema` validators, indexes. `--describe` needs no server |
| `mongo/load.py` | The loader. Drops, rebuilds, stamps provenance |
| `mongo/queries/` | Eight runnable, commented query files |
| `mongo/tests/test_load.py` | 20 tests: idempotency, provenance, validation, card semantics |
| `mongo/requirements.txt` | `pymongo`, kept out of `backtester/requirements.txt` on purpose |

## Scope

This component reads the repo and writes one local database. It places no orders,
reaches no network, and touches no database other than `solmargintrader`. Nothing
in `backtester/`, `research/`, `extension/` or `soltui/` imports it, so the store
can be rebuilt or dropped without affecting any of them.
