# mongo/ — the local research store

A read-mostly MongoDB copy of everything this repo has measured: price history,
strategies and their cards, the signal and indicator layers, per-bar readouts,
backtest runs, CPCV and sweep results, the coin write-ups, and the test-suite
results. The derived `solmargintrader` database defaults to `localhost:27017`;
its document count depends on the source artifacts available when loading.

The files on disk stay the source of truth. This is a derived store, which is why
the loader can drop and rebuild it without asking.

> Research and educational tooling, not financial advice. Every figure here is a
> mechanical measurement over cached history. Read `docs/known-issues.md` before
> treating any of it as current.

## Setup

```bash
uv venv .venv --python 3.13                 # first setup only; reuse an existing .venv
uv pip install --python .venv/bin/python -r mongo/requirements.txt -e ./backtester

.venv/bin/python mongo/schema.py --describe  # the layout, no server needed
.venv/bin/python mongo/load.py --dry-run     # counts only; no MongoDB connection
```

The commands run from the repository root. The MongoDB driver and backtester
dependencies stay inside `.venv`; activation is optional because each invocation
names the interpreter. The CLI reports a known missing package with exit code 3
and an exact isolated-environment installation command. It does not install
packages or start MongoDB. `python-dotenv` is needed by the separate market-capture
tool, not by the MongoDB research loader.

To rebuild the local derived store, ensure your configured MongoDB service is
already available, then run `.venv/bin/python mongo/load.py`. Add `--run-tests`
only when you intend to execute the configured research suites and record their
observed results; those suites require their own documented dependencies.

Verify the component:

```bash
.venv/bin/python -m unittest discover -s mongo/tests -t .
mongosh solmargintrader mongo/queries/08-provenance-and-health.js
```

Native integration tests use a generated `solmargintrader_test_<uuid>` database,
seed tracked reference fixtures, and clean up only that database. They skip when
MongoDB is unavailable. The remaining tests use mocks and temporary files.

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

Run `.venv/bin/python mongo/load.py --dry-run` for the current artifact counts.

| Collection | Shape |
| --- | --- |
| `bars` | **Time series.** `ts` + `series` meta `{asset, interval, source, frame_checksum}` |
| `spot_prices` | **Time series.** The JLP snapshot — not OHLCV, see below |
| `equity_points` | **Time series.** `ts` + `curve` meta `{run_id, strategy}` |
| `strategies` | One per loaded strategy card, with live registry facts when a registry key is present |
| `signals` | The stateless one-bar rules from `research/decide.py` |
| `indicators` | Reported rows and explicitly skip-listed functions |
| `decisions` | One per readout, exactly as `decide.build_report()` emits it |
| `backtest_runs` | Manifest + per-strategy metrics |
| `trades` | One per fill |
| `experiments` | One per result file: kind, columns, object sidecar |
| `experiment_rows` | One per result row. `section` is `result` or `summary` |
| `documents` | Markdown: coin spokes, research prose, component docs |
| `test_results` | A suite count + outcome per commit, from a real run |

### Four design decisions you will run into

**Bars are a native time series collection.** Filter on `series.*` and a time
range; MongoDB maintains the meta+time index itself and there are no user indexes
to add. Provenance lives on the metaField, where it is stored once per bucket
rather than once per bar.

**`spot_prices` is separate.** `data/JLP_spot.csv` is a Jupiter
price snapshot with columns `timestamp,iso,mint,usd_price,source` — no OHLCV at
all. `research/decide.py` refuses to read it as bars, and merging the two here
would contradict the distinction the code enforces.

**Strategy cards keep their own vocabulary.** There is no `registered` boolean.
`registry_key` is a string when a card maps to a registered `Strategy` implementation and
`null` otherwise. A null key alone does not mean unimplemented. Use `status`
(`measured` / `implemented` / `spec-only`) and `runner` to interpret the card.

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

The loader hashes the exact byte snapshot it parses for CSV, JSON and Markdown.
Source columns cannot overwrite loader metadata; colliding fields stay under
`source_fields`. A shared manifest snapshot binds a run and its strategy artifacts.
Only manifest-declared strategies load, and every curve/trade file must match its
`artifact_sha256` entry. The report writer publishes this inventory in the manifest
after writing the artifacts. Legacy output without those hashes must be regenerated;
the loader refuses it rather than assigning stale files to a new run.
`--only` validates names before connecting or dropping collections and recreates only
the selected collections. Empty/unknown selectors refuse.

## Files

| Path | What it does |
| --- | --- |
| `mongo/schema.py` | Collection specs, `$jsonSchema` validators, indexes. `--describe` needs no server |
| `mongo/load.py` | The loader. Drops, rebuilds, stamps provenance |
| `mongo/cli.py` | Shared CLI prerequisite messages; library imports keep their normal behavior |
| `mongo/queries/` | Eight runnable, commented query files |
| `mongo/tests/test_load.py` | Isolated native fixtures, provenance, validation, card semantics |
| `mongo/tests/test_query_scripts.py` | Inert mongosh examples, fixture isolation, interpreter and CLI regressions |
| `mongo/requirements.txt` | `pymongo`, kept out of `backtester/requirements.txt` on purpose |

## Scope

This component reads the repo and writes one local database. It places no orders,
reaches no network, and touches no database other than `solmargintrader`. Nothing
in `backtester/`, `research/`, `extension/` or `soltui/` imports it, so the store
can be rebuilt or dropped without affecting any of them.

## Rebuilding without deleting test receipts

`python3 mongo/schema.py --create` rebuilds derived collections, but retains `test_results`
and updates its validator and indexes in place. These test receipts are original observations;
the loader cannot regenerate them. Deleting them requires the explicit
`python3 mongo/schema.py --create --reset-test-results` command. The reset flag refuses with
`--keep` or without `--create`.
