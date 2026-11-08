# executor — agent rules

Guarded spot swaps on Solana through Jupiter. **It signs and sends real transactions from the owner's wallet.**
Treat every change as production software. Read the root `CLAUDE.md` "Live on-chain actions" first; its six
conditions bind you here too.

## Authorization and its limits

- The owner's standing live authorization (root `CLAUDE.md`, last given 2026-11-06) covers the owner's Solana wallet
  `EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV` and the key file `~/.ssh/solana.private`.
- Owner decisions of 2026-11-07: per-strategy max position $25 and daily loss stop $10 (both configurable, these are the
  defaults); first venue is Jupiter on Solana, spot only, long or flat, no shorts; the research gate is mandatory and
  only an explicit, logged config flag overrides it.
- Never read, print, copy or hash the key file. The program loads it itself and refuses it unless it is a regular
  file, owned by you, mode 600 or stricter, and its public key equals the configured owner.
- Never raise a limit in `~/.executor/config.toml` (`max_position_usd`, `daily_loss_stop_usd`, `max_trade_usd`,
  slippage, impact, deviation, priority-fee, reserve, `allowed_mints`) without the owner asking in that session.
- Never write `allow_failed_research_gate = true`, and never record a research `pass` that did not happen. Those are
  the owner's decisions.
- Code defaults stay dry-run. A fresh install must never sign. Live needs `mode = "live"` in the config AND `--live`
  (or `live: true`) on the call.

## Non-negotiables

1. **Verify before you sign.** `txverify.py` runs on every transaction Jupiter returns, and again on the exact signed
   bytes. An unknown program, an unknown instruction type, a foreign fee payer, a second signer, an unresolved
   lookup table, a touched token account outside the swap, a third-party lamport movement, or a balance delta that
   disagrees with the quote is a refusal. Never relax a check to make a transaction pass: read the transaction.
2. **Never guess a number that becomes an order.** A missing independent price, a missing SOL price for fees, an
   unknown token or decimals, a malformed quote field: refuse. Do not fall back to config and do not default to zero.
3. **Rails are code and fail closed** (`rails.py`, `gates.py`). A rail documented but not enforced is not a rail.
4. **Journal before send, outcome after** (`journal.py`). Intent, then `sending` with the signature, then the send, then
   the result. A send that errors or times out is `unknown`, **never auto-retried**; `executor reconcile` resolves it
   from chain. An unknown blocks every new live swap.
5. **One send per swap.** `Rpc.send_transaction` makes one attempt and has no retry. Reads may retry; the send may not.
6. **Dry-run simulates what live would send.** The two paths share every step up to the signature. A change that
   makes dry-run weaker than live is a bug.
7. **One registry, two surfaces.** Every action is a command in `registry.py`. The CLI and the HTTP API only carry bytes;
   `tests/test_surfaces.py` proves the envelopes are byte-identical. Do not add logic to `cli.py` or `api.py`.
8. **No secrets in logs, journal, envelopes or exceptions.** The call log holds parameter keys only. Key errors say what
   is wrong with the file, never what is in it.
9. **Exits are never gated.** `swap --exit` (a reduce-only sell of a tracked position) is not stopped by KILL, the daily
   loss stop, the gates or `max_trade_usd`. Everything else still applies (allowlist, slippage, impact, verifier).

## The reserved strategy `path-validation`

It exists to prove the live path with a tiny real swap, and for nothing else. It needs `[validation].enabled = true`
(default false), skips the soak and research gates, and is capped **in code** (not config) at $2 per trade and $4 per
rolling 24 h. It may sell wallet SOL that no strategy bought. Turn the flag back off after use. It is not a way around
the gates for a real strategy: any other id, including `path-validation-2`, gets the full gates.

## Rails (all in `~/.executor/config.toml`, created mode 600)

| Rail | Default | Applies |
| --- | --- | --- |
| `max_position_usd` | 25 | per strategy, cost basis of the open position, buys |
| `daily_loss_stop_usd` | 10 | per strategy per UTC day: realized loss + fees + open unrealized loss; stops buys |
| `max_trade_usd` | 10 | one swap, valued by the independent price |
| `max_slippage_bps` / `max_price_impact_bps` / `max_price_deviation_bps` | 50 / 50 / 100 | quote |
| `max_priority_fee_lamports` | 200000 | verifier, from the compute-budget instructions |
| `min_sol_reserve_lamports` | 5000000 | the simulated post-swap native balance |
| `allowed_mints` | SOL, USDC | tokens must also be in `tokens.py` |
| `gates.soak_hours` / `min_dry_runs` | 24 / 5 | live, per strategy |
| research gate | required | live, per strategy; `executor gates record-research` |
| `KILL` file | absent | live (not `--exit`) |

## Code rules

- `rails.py`, `ledger.py`, `txverify.py` (layer 1) and `quote.py` are pure: no I/O. Unit-test every branch.
- Contract/program addresses live in `txverify.py` only. Change them only when two sources agree.
- A new instruction the verifier does not decode is a refusal until someone decodes it, with a malicious fixture.
- Every new refusal needs a test that would fail if the check were removed.
- Verify with `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests && .venv/bin/pytest -q`
  (offline) and `.venv/bin/pytest -q -m network` (live read-only: quote, build, simulate; never sends).

## Known gaps (do not present these as working)

- **Cross-chain execution is not built.** `quote --to-chain base` is quote-only through LI.FI; it drops the
  `transactionRequest`. Executing a bridge needs a verifier for another chain's transactions.
- **The live strategy runner and the soltui "Run live" button are not built here** (workstream E2).
- Jupiter marks Swap API v1 (Metis) as no longer actively maintained and superseded by Swap V2. The owner chose v1
  on 2026-11-07. Moving to V2 is a decision, not a silent change.
- Only spot, long or flat, against USDC. No shorts, no perps, no other quote assets.
- The keyless Jupiter host rate limits hard; calls are spaced and a 429 is retried a bounded number of times.
- Fees are valued with the SOL reference price at quote time.
- `priceImpactPct` is read as a fraction (0.0012 = 12 bps), checked against live quotes on 2026-11-07.
