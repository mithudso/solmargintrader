# executor — guarded Solana swaps

The **executor** component of solmargintrader: best-price spot swaps on Solana through Jupiter, behind a semantic
transaction verifier, hard rails, a research gate, a dry-run soak and an append-only journal.

> **It can move real money.** Code defaults are dry-run. Live needs `mode = "live"` in `~/.executor/config.toml`
> AND `--live` on the call. Not financial advice. Read `CLAUDE.md` before changing anything.

## Install and verify

```bash
cd executor
uv sync --extra dev -p 3.13
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
.venv/bin/pytest -q                  # offline, recorded fixtures
.venv/bin/pytest -q -m network       # live read-only: quote, build, simulate (never signs)
```

## Use

```bash
executor quote --from SOL --to USDC --amount 0.01            # route, impact, minOut, second price reference
executor quote --from USDC --to USDC --amount 5 --to-chain base   # quote only; cross-chain execution is not built
executor swap  --from SOL --to USDC --amount 0.01 --strategy my-strategy   # dry-run: simulates what live would send
executor swap  --from SOL --to USDC --amount 0.01 --strategy my-strategy --live --reason "why"   # live
executor swap  --from SOL --to USDC --amount 0.01 --strategy my-strategy --exit --live --reason "stop"
executor status | journal [--limit N --strategy S] | gates --strategy S | reconcile
executor gates record-research --strategy S --result pass --source <report>
executor kill [--reason R]      executor resume --confirm
executor list                    # every command, its params and types
executor call <name> --json '{...}'
executor api [--port 8789]      # loopback HTTP API; token in ~/.executor/api-token (mode 600)
```

Amounts are decimal strings (never floats). Every call returns one envelope, identical on the CLI and the API:

```json
{"ok": true,  "command": "swap", "result": {...}, "error": null}
{"ok": false, "command": "swap", "result": null, "error": {"code": "refused", "message": "refused: ..."}}
```

Codes: `bad_params`, `unknown_command`, `forbidden` (missing `confirm`, bad token), `refused` (a rail, gate or the
verifier said no; nothing was sent), `failed`, `timeout`, `ambiguous` (a send may or may not have landed: journalled
as `unknown`, never retried, resolve with `executor reconcile`).

HTTP: `GET /v1/health` (no auth), `GET /v1/commands`, `GET /v1/<read-only command>?a=1`, `POST /v1/<command>` with a
JSON object. Binds 127.0.0.1, needs `Authorization: Bearer <token>`, refuses any request with an `Origin` or
`Sec-Fetch-Site` header, sends no CORS headers. Every call appends one line to
`~/Library/Logs/executor/calls.jsonl` (surface, command, ok, error code, ms, parameter keys; never values).

## How a swap is made

`resolve -> quote + independent price -> rails -> /swap -> decode -> verify (static) -> pre-state -> simulate ->
verify (economic)`, and dry-run stops there. Live continues: `load key (mode 600, owner match) -> sign -> check the
message is unchanged -> re-simulate the exact signed bytes -> re-check rails -> journal intent -> journal sending ->
send once -> confirm -> read the chain -> verify the post-trade balances -> journal result`.

The verifier (`src/executor/txverify.py`) checks, before anything is signed: fee payer is the owner and the only
signer; every program is on the allowlist (Jupiter v6, SPL Token, Token-2022, Associated Token, Compute Budget,
System) and runs only the instructions listed for it; the priority fee is bounded; SOL leaving through System
instructions is bounded; ATAs are only the owner's; the simulation succeeds; no token account of the owner outside the
swap changes; no third-party wallet is paid; input falls by exactly the quoted amount, output rises by at least
`minOut`, SOL falls only by fee, retained rent and the input; the owner keeps the SOL reserve.

## State

| File | Contents |
| --- | --- |
| `~/.executor/config.toml` | rails and limits, mode 600, created with safe defaults |
| `~/.executor/journal.jsonl` | append-only intents, sends, results, unknowns |
| `~/.executor/soak.json`, `research-gate.json`, `gate-overrides.jsonl` | gates |
| `~/.executor/KILL` | halts live swaps (not `--exit`) |
| `~/.executor/api-token` | HTTP bearer token, mode 600 |
| `~/Library/Logs/executor/calls.jsonl` | one line per call, parameter keys only |

## Journal and gate integrity

Journal writes complete every byte and sync before returning. Invalid JSONL envelopes, sequences,
signatures or state transitions block new appends and live swaps. Diagnostics identify the line and
reason without echoing damaged payloads. Preserve the original journal and inspect the damaged record;
deleting an uncertain send can permit a duplicate trade. Reconciliation never resubmits a transaction.

Reconciliation shares the swap lock. A present `processed` status remains unresolved even after blockhash
expiry; only confirmed/finalized evidence, or an absent status after the existing expiry margin, can
resolve it. Missing token-balance arrays or invalid/duplicate account indices remain unknown. An explicit
empty array can describe a new account. Failed on-chain transactions still incur network fees; measured
fees count toward the daily loss stop. If their fee evidence is unreadable, reconciliation retains the hold.
Older failed records without measured fees refuse loss accounting for that strategy and day until inspected.
If KILL appears during journal persistence, the executor records a pre-send rejection and sends nothing.
Quotes are rechecked for expiry after journal writes. Reduce-only exits retain their existing KILL exemption;
quote freshness and transaction verification still apply.

Soak records require finite, internally consistent credit. Invalid credit restarts at the next successful
dry-run. Research records require the expected schema, finite timestamps, pass/fail results and a source.
Damaged research evidence blocks the gate and further writes until inspected; it cannot revive an older
pass. Backwards timestamps within a strategy also block the gate while preserving the later-recorded result.
Stable sidecar locks serialize both gate writers across threads and processes. Do not remove the lock files
while an executor call is running.

Offline regressions for these cases live in `tests/test_journal_integrity.py`, `tests/test_gate_integrity.py`
and `tests/test_engine_integrity.py`. They use temporary homes, synthetic keys and a fake chain. No test sends
a real transaction or changes the owner's gates.
