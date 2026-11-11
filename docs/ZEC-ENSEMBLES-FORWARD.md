# ZEC ensemble paper forward owner

`ecosystem.zec_forward` runs ten frozen selected ZEC ensembles as independent,
long-or-flat virtual spot accounts. The backtester supplies the exact policy
builder and next-observed-open engine. The source is Binance public spot
`ZECUSDT`, labelled `ZEC/USDT`. USDT is never silently converted to USD.

Each account begins with 10,000 USDT virtual capital and its selected explicit
cost configuration. The study assumes 10 basis points fee and 2 basis points
slippage per side. This is modelled reference accounting, not observed execution,
capital allocation, a probability of profit, or a live-order capability.

The owner freezes the top-ten selection artifact and its hashes. It seeds the
indicator state from the study's exact observed-history origin. New complete
native candles extend that state. Seed data creates no historical paper trades.
The first decision requires a fully closed candle after activation. Only a later
observed candle open can apply that target in the canonical model. Poll receipt
latency is recorded; the next-open reference price does not establish an
executable contemporaneous fill.

## Commands

Use the stable environment containing the released backtester and ecosystem
packages. `init` requires the study's contiguous prepared CSV files, not a raw
long-history CSV with a different origin. The selection binds each file hash.

```sh
python -m ecosystem.zec_forward --home /absolute/path/to/forward init --selection /absolute/path/to/top10.json --seed-1m /absolute/path/to/study/ZEC_1m.csv --seed-1h /absolute/path/to/study/ZEC_1h.csv
python -m ecosystem.zec_forward --home /absolute/path/to/forward status
python -m ecosystem.zec_forward --home /absolute/path/to/forward run
python -m ecosystem.zec_forward --home /absolute/path/to/forward publish --ui-home /absolute/path/to/ecosystem-home
python -m ecosystem.zec_forward --home /absolute/path/to/forward install-service
```

`init` is idempotent only for the same selection hash. It fetches newer closed
candles to refresh the warmup without opening a paper position. The macOS
`install-service` command installs a user LaunchAgent with `RunAtLoad` and
`KeepAlive`. The installed interpreter must remain at its stable absolute path.
The service uses one exclusive owner lock and records its heartbeat in SQLite.

The existing `/api/oracle` read contract carries `selected_experiment` metadata.
When the requested instrument is `ZEC/USDT`, it returns the selected candidate's
actual long-or-flat target and native candle horizon. The UI selects this
publication on initial load and displays the ten accounts and exact winning
configuration. Other instruments retain their existing owner evidence. Voter
checkboxes do not change a frozen ensemble experiment.

## Freshness and recovery

No incomplete candle enters a signal. Source gaps, stale observations, missing
owners and a failed study read withhold the Oracle signal. A process restart
continues the exact account and policy checkpoint if it has not missed decision
bars. A gap or outage longer than two native candle intervals plus thirty seconds
blocks the account with `forward_source_gap` or
`missed_forward_bars_review_required`. The book remains preserved; the service
does not manufacture historical decisions or reset held inventory. Review the
blocked account before beginning a new separately identified experiment.

Each database stores its frozen selection, seed provenance, observed candles,
decisions, modelled fills and account continuation. A private publication pointer
under the UI home identifies the selected study without copying or altering the
existing Oracle archives. Reads do not create stores or start services.
