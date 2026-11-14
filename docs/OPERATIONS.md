# Extension operations runbook

This guide covers the extension's grid engine and its separate CLI/local HTTP
state. Oracle's optional TradingView worker, the standalone executor and managed
paper owners have their own boundaries and runbooks. Source tests do not authorize
or establish live execution.

## Stop the selected owner

From the repository root, this command kills the CLI's selected local state:

```bash
(cd extension && node tools/cli.js kill)
```

`kill` latches that owner's kill switch and disarms it until explicitly cleared.
A stray `arm` cannot resume it. The browser extension has separate IndexedDB and
configuration state: use its popup's red KILL SWITCH button to stop that browser
owner. A CLI kill does not stop another store, browser profile, Oracle worker,
executor or paper process. Identify each actual owner before acting; see
[incident scope and reconciliation](runbooks/incident.md).

`kill` does not cancel resting venue orders or reverse an in-flight request. Read
the selected owner's journal and inspect venue state before attempting any
separately authorized cancellation. The CLI data view is:

```bash
(cd extension && node tools/cli.js data --json)
```

Keep unknown intents and transaction/order identities until venue evidence resolves
them. Do not delete state or retry a write because the local process stopped.

## Current Trigger live gate

The bundled Trigger adapter refuses live placement without a signer that implements
`signVerifiedTriggerDeposit`. Its `capabilities.canPlaceLive` is false when that
trusted transaction-intent verifier is absent. The bundled session-key signer does
not supply it. Creating or funding a key, choosing `full-auto`, or confirming an arm
does not satisfy this gate. Keep fresh installs dry-run and disarmed; do not attempt
to bypass the refusal.

The deterministic offline economics gate can be run without credentials, funding
or arming the installed owner:

```bash
(cd extension && npm test)
(cd extension && node tools/dryrun.js --ticks 8 --osc 6 --offline 100)
```

Its round trip must close positive. This verifies the simulated rung/lot economics,
not authenticated wallet responses, real execution valuation, fee attribution or
live signing. See [the Trigger contract](jupiter-trigger-contract.md) and
[testing limits](TESTING.md). A future independently verified live path needs its
own owner-authorized acceptance plan; one test order cannot close all those gaps.

## Daily checks

From the repository root:

```bash
(cd extension && node tools/cli.js status)
(cd extension && node tools/cli.js pnl)
```

Watch for:

| Signal | Meaning |
| --- | --- |
| Intents stuck in `unknown` | A submit was ambiguous. Reconcile them by hand against the venue — the engine will never auto-retry |
| A placement call throws, or persistence fails after acceptance | The current engine records `unknown`; the venue may have accepted it. Never auto-retry |
| Intents in `failed` | Inspect the recorded cause. A pre-submit stop with `definitelyNotSubmitted` differs from an ambiguous venue call; a historical `failed` label alone proves no absence |
| `lastTickDeltaMs` far above your `tickSeconds` | Chrome clamped the alarm, or the worker is being killed |
| `realizedPnlUsdToday` at the daily limit | The daily-loss rail blocks new admission. A new UTC day resets this counter; other rails, kill state and ambiguity holds still apply |
| Rising `feeTotalUsd` with flat `roundTripCount` | Paying to trade without capturing spread. Stop the affected owner and inspect rung spread, costs and fill evidence |
| `unmatchedSellQty` above zero | A sell had no lot behind it. The fill log is incomplete |

## Common situations

**A tick reports `venue returned an unusable price`.** Correct behaviour — the tick aborted rather
than writing a NaN into P&L. Check Jupiter's status and `node tools/cli.js price`.

**Leverage is refused.** Trigger V2 is a spot venue. The extension refuses an
incompatible leverage setting rather than trading unleveraged while claiming otherwise.
The extension's Perps adapter remains read-only. Oracle's separate GUM ZEC worker
does not enable leveraged orders in this adapter.

**An authenticated request returns 401/403.** The adapter can refresh authentication
once on its eligible read path. Persistent refusal requires checking the actual account,
key permissions and provider response category without exposing credentials. It does
not prove an ambiguous order was absent or authorize another submit.

**Rate limited (429).** Eligible reads use bounded backoff and `Retry-After`; a
per-attempt budget limits requests. Writes are not automatically replayed. Reconcile
an ambiguous submission before deciding the next action; a rate-limit observation
does not grant permission to change strategy or risk parameters.

**The service worker seems dead.** MV3 terminates it when idle; it wakes on the alarm. Confirm with
`chrome://extensions` → Service worker → Inspect, and check `lastTickMs` in `status`.

## Recovering local state

The journal is a plain JSON file (`~/.solmargintrader/journal.json`, or IndexedDB in the browser —
the two are separate).

Preserve the complete journal and configuration as well as any exported fills before
an explicitly authorized state reset. `exportCsv` is a fill export, not a complete
submission/ambiguity backup. `reset` erases only the selected local history; it does
not cancel venue orders, resolve unknown submissions or clear another owner's state.
Do not reset as a recovery shortcut. Reconcile first and retain evidence; follow
[the rollback guide](runbooks/rollback.md) when reverting source.
