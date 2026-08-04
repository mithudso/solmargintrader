# Testing

```bash
python3 -m unittest discover -s backtester/tests -t .   # 80 tests
cd extension && npm test                                # 96 tests
```

176 tests total, no test-framework dependency in either component (`unittest` and `node:test`).

## Extension — what the 96 tests cover

| Area | Examples |
| --- | --- |
| Grid math | Arithmetic and geometric ladders against hand-computed values; endpoint pinning; degenerate configs rejected |
| **Round-trip economics** | An exit rests one rung above its lot, never at the same level; `gross === notional × rungWidth` |
| Planning | Lot aggregation (two lots on one rung produce **one** order, not a duplicate key); venue minimum; deadband; already-resting suppression |
| Risk rails | Each rail fires on its own breach; a batch cannot collectively breach a cap each member passes; rails **fail closed** on missing or NaN state; unusable orders blocked |
| P&L | FIFO across lots; partial closes realizing a proportional share of entry fees; carry subtracted; fees turning a gross win into a net loss; unmatched sells surfaced |
| Reconciliation | A venue echoing fewer decimals is matched, **not duplicated**; a missing order is orphaned and never auto-retried; unknown live orders adopted; two near-identical orders do not bind to one intent |
| Tick guards | Unusable price aborts before P&L; the daily counter measures today, not lifetime; a short grid on a spot venue says so |
| Wallet | base58 against real mints and the all-zero pubkey; shortvec boundaries; signature insertion into the correct slot; non-signer refused |
| Crypto | Sealed-seed round trip; wrong passphrase fails closed; fresh salt and IV per seal; Ed25519 signing |
| **Surface parity** | Every command routable over the API; `GET` restricted to read-only; CLI help lists all commands and every argument; UI messages all map to real commands |

The parity suite probes all 22 commands with a deliberately invalid argument, which proves the route
resolved **without executing the handler** — no side effects, no network calls.

## What is NOT covered

Read this before trusting anything with money.

1. **No live order has ever been placed.** The write path (auth → vault → deposit craft → sign →
   create) matches the documented shapes but has never executed. It needs an API key and a funded
   wallet. Test with one rung at the $10 minimum.
2. **The Trigger order-list response envelope is guessed.** `normaliseOrders()` infers field names for
   the orders/history endpoint, and reconciliation depends on them. Verify against a real response.
3. **Fee attribution is unconfirmed.** Fills take `feeUsd` from the venue when present and 0
   otherwise. Zero fees make a grid look better than it is.
4. **Signature insertion is tested against synthetic transactions**, not a real Jupiter deposit.
5. **Loading unpacked in Chrome is not automated.** `chrome://extensions` requires a human. The
   headless dry run is the integration gate instead; the CI job validates the manifest statically.
6. **The Chrome alarm floor is assumed to be 30s.** The engine logs the real wake delta — watch it
   before trusting a sub-minute tick.

## Verification commands

```bash
cd extension

npm test                                              # unit + parity
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # a round trip must close positive
node tools/dryrun.js --ticks 4 --walk 5 --offline 100 # trending case: bids fill, no exits
node tools/verify-endpoints.js                        # live Jupiter reachability
find src tools test -name '*.js' -print0 | xargs -0 -n1 node --check
```

The oscillating dry run is the meaningful one: it is the only check that closes a round trip and so
the only one that can detect a zero-spread regression.

## Backtester — 80 tests

Correctness of the simulation is the priority, so the suite concentrates on the things that silently
inflate a result: **lookahead leaks**, cost application, and metric arithmetic. Any change touching
signal generation or fill timing needs a test that would catch a one-bar leak. See
`backtester/README.md`.

## Adding tests

- Extension: `extension/test/*.test.js`, `node:test` + `node:assert/strict`. Assert behaviour and
  observable effects, not line execution.
- Backtester: `backtester/tests/`, `unittest`.
- A new command needs no new parity test — the registry-driven suite picks it up automatically. If it
  takes an argument that changes money, add a behavioural test for that argument.
