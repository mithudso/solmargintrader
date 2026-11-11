# Operations runbook

## Stop everything

```bash
cd extension && node tools/cli.js kill
```

`kill` is latching: it disarms **and** blocks every rail until you run `clearKill`. A stray `arm`
cannot resume trading. In the extension, the popup's red KILL SWITCH button does the same thing.

`kill` does **not** cancel resting venue orders. To remove those:

```bash
node tools/cli.js data --json          # find venueOrderId values
node tools/cli.js cancelOrder --venueOrderId <id>
```

## Dry run to live, in order

Do not skip steps. Each one can fail cheaply; the next one cannot.

1. **Shape the grid and read the economics.**
   ```bash
   node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7 --notionalPerRungUsd 12
   node tools/cli.js levels     # rung width and gross per round trip
   node tools/cli.js capital    # what it needs funded
   ```
   If gross per round trip is not comfortably larger than two fills' fees plus slippage, the grid
   cannot win. Widen the rungs or stop here.

2. **Confirm the plan matches your intent.**
   ```bash
   node tools/cli.js plan --price <current>
   ```
   Every sell must sit one rung above a lot you hold. No sell should share a price with its entry.

3. **Run it in dry-run for a while.** Real prices, simulated fills, zero writes.
   ```bash
   node tools/cli.js arm
   node tools/cli.js tick --count 5
   node tools/cli.js pnl
   ```

4. **Set the rails deliberately.** The defaults are conservative, not correct for you.
   ```bash
   node tools/cli.js setLimits --maxTotalNotionalUsd 250 --dailyLossLimitUsd 25 --maxOrdersPerTick 2
   ```

5. **Add credentials.**
   ```bash
   node tools/cli.js setApiKey --apiKey <key-from-developers.jup.ag/portal>
   ```

6. **Choose a signing mode.** `semi-auto` approves each signature by hand and cannot run unattended.
   `full-auto` needs a dedicated key funded with grid capital only:
   ```bash
   node tools/cli.js createSessionKey --passphrase '<12+ chars>'
   # fund the printed address with working capital ONLY, then:
   node tools/cli.js setConfig --mode full-auto
   ```

7. **Go live at the smallest possible size.** One rung at the $10 venue minimum, and watch it.
   ```bash
   node tools/cli.js setConfig --rungs 2 --notionalPerRungUsd 10
   node tools/cli.js arm --confirmLive
   node tools/cli.js tick
   node tools/cli.js data --json
   ```
   Confirm the order exists on the venue and that `reconcile` matches it on the next tick before
   scaling up. This is the step that validates everything listed as unverified in
   [TESTING.md](TESTING.md).

## Daily checks

```bash
node tools/cli.js status | head -40
node tools/cli.js pnl
```

Watch for:

| Signal | Meaning |
| --- | --- |
| Intents stuck in `unknown` | A submit was ambiguous. Reconcile them by hand against the venue — the engine will never auto-retry |
| Intents in `failed` | The submit threw. Safe to retry, and the next tick will re-plan |
| `lastTickDeltaMs` far above your `tickSeconds` | Chrome clamped the alarm, or the worker is being killed |
| `realizedPnlUsdToday` at the daily limit | The engine has halted for the UTC day. It resumes tomorrow |
| Rising `feeTotalUsd` with flat `roundTripCount` | Paying to trade without capturing spread. Stop and re-check step 1 |
| `unmatchedSellQty` above zero | A sell had no lot behind it. The fill log is incomplete |

## Common situations

**A tick reports `venue returned an unusable price`.** Correct behaviour — the tick aborted rather
than writing a NaN into P&L. Check Jupiter's status and `node tools/cli.js price`.

**Leverage is refused.** Trigger V2 is a spot venue. `leverage > 1` there is unreachable, so the
engine refuses to tick rather than trading unleveraged while the config claims otherwise. Set
`--leverage 1`, or wait for the Perps write API.

**Every order fails with 401/403.** The JWT was rejected. The venue adapter clears and re-authenticates
once automatically; if it persists, the API key is wrong or revoked.

**Rate limited (429).** The client backs off and honours `Retry-After`, and a per-tick budget caps
requests. If it recurs, raise `tickSeconds` or lower `maxOrdersPerTick`.

**The service worker seems dead.** MV3 terminates it when idle; it wakes on the alarm. Confirm with
`chrome://extensions` → Service worker → Inspect, and check `lastTickMs` in `status`.

## Recovering local state

The journal is a plain JSON file (`~/.solmargintrader/journal.json`, or IndexedDB in the browser —
the two are separate).

```bash
node tools/cli.js exportCsv > fills-$(date +%F).csv   # back up before anything destructive
node tools/cli.js reset --confirm                     # erases LOCAL history only
```

`reset` does not cancel venue-side orders. Cancel them first, or you will have live orders with no
local record — the reconciler will adopt them on the next tick, which is recoverable but noisy.
