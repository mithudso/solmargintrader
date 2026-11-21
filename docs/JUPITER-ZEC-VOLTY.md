# ZEC Volty 25× bot

Open either [ZEC long](https://jup.ag/perps/long/USDC-ZEC) or
[ZEC short](https://jup.ag/perps/short/USDC-ZEC) and find **ZEC Volty 25×** in
the SolMarginTrader Perps window. The host follows one strategy on both pages.
Chrome can be closed while the host is running.

The bot uses the ungated breakout from the [frozen Volty study](../research/papers/results/zec_gum_25x_5m_card_1.md).
The most recent completed five-minute close sets the center of the next
five-minute window. Add and subtract 1.5 times the mean true range from the last
ten completed bars to get the upper and lower levels. A fresh mark reaching the
upper level targets a long. A fresh mark reaching the lower level targets a
short. The bot waits for a fresh pair of marks in the current window after
startup or a data gap. It ignores same-side signals while it holds a position.

An opposite signal first closes the current position with a reduce-only order.
The bot opens the new side after GUM confirms the close, the account is flat and
collateral has settled, while the signal is still in its five-minute window and the market feed is fresh.
Each order uses a price-capped Fill-or-Kill Action. An ambiguous submission is reconciled from GUM
history and is never resent automatically. Take-profit and stop-loss brackets are
disabled. The original paper return included a stop and a fixed paper size.

## Observe

From a checkout with the Oracle and SolTUI native runtime installed:

```sh
python -m oracle.zec_volty --watch
```

Open the ZEC panel and expect **Observe** and a recent update. Once the market
crosses a level, the signal appears with its timestamp and direction. The
observe process requires no account or signer and places no orders. The
SolTUI [native messaging host](../soltui/README.md#the-command-bridge-one-registry-four-surfaces) reads
status from the local default state directory `$HOME/.soltui/zec-volty`.

## Funded mode

Use a separate GUM parent and subaccount dedicated to this bot. The parent
needs funded USDC collateral and an explicit **isolated ZEC 25×** leverage
preference. Enter the owner and account's **public** identifiers, a local
owner-matching key file path, and the specific size and slippage limits in a
private JSON policy. Set its permissions to mode 600. The host reads this file
locally. The Chrome panel has no signer or order controls.

| Policy field | Meaning |
| --- | --- |
| `owner` | GUM owner's public address |
| `trading_account` | Dedicated GUM parent public address |
| `subaccount_id` | Dedicated subaccount number |
| `key_file` | Absolute path to the owner's private signer file |
| `allocation` | Owner-selected percentage in the range 0 to 75, excluding zero |
| `allocation_basis` | `collateral` or `notional` |
| `max_slippage_bps` | Owner-selected order price cap in basis points |
| `max_order_notional_usdc` | Absolute USDC ceiling on each new entry before signing |

GUM collateral is held separately from wallet USDC. Funded mode checks the
account and venue state and refuses sizes below the venue minimum or outside
the chosen cap. The venue preference is 25×. Fees, lot rounding, and fill
price affect realized effective leverage. The notional ceiling uses the quote
checked before signing. An improved short fill can execute at a higher USD
price than that quote.

With the private policy path stored in `VOLTY_POLICY`, check the account and
size without submitting an order:

```sh
python -m oracle.zec_volty --preflight --config "$VOLTY_POLICY"
```

Stop the observe process before starting the funded owner:

```sh
python -m oracle.zec_volty --watch --live --config "$VOLTY_POLICY"
```

The default journal and status file share the same private state directory.
Keep the journal when restarting. To pause orders, create a file named `KILL`
in the state directory. The pause does not close positions. Leave the owner
running to reconcile outstanding submissions.

### Changing the allocation on a funded journal

Allocation is part of the binding used to identify orders. Copy the current
private policy and change only `allocation` in the candidate. After the
watcher stops, run the allocation rotation against the existing state directory.
The command takes both owner locks and requires a flat account, zero open
orders, no unresolved journal entries and verified fill lineage. It preserves
the binding and receipts of every earlier event.

```sh
python -m oracle.zec_volty --rotate-allocation-from "$VOLTY_POLICY" \
  --config "$VOLTY_NEW_POLICY" --state-dir "$VOLTY_STATE"
```

Run preflight with the candidate policy and the same state directory before
restarting the watcher on that policy. The separate opening-notional ceiling
still applies to every order. If a policy change is blocked on reconciliation,
a signed, finalized Jupnet instruction failure can establish a rejection even
when GUM has no order history row. Match the transaction to the original
account and every committed instruction field before recording that outcome.

## Verify trading

The **ZEC Volty 25×** panel shows the host heartbeat and the current GUM mark
with its timestamp, long trigger, short trigger and five-minute window end.
Trigger levels clear when the observation is stale or the window ends. Open
**Signal history** for recent decisions, including skipped crossings and expired
signals. Historical receipts remain visible if the host goes stale.

Open **GUM order receipts** for the execution legs. **Acknowledged** means GUM
accepted the request. **Pending** means the venue outcome is still being
reconciled. A filled close can still be **awaiting collateral settlement**.
Use the client order ID to correlate the request before a venue
order ID is available. A confirmed fill shows the GUM order ID, filled
quantity, fill price, fee and venue transaction signature.
Compare the order ID or fill transaction with the history for the same GUM
subaccount. A stale or unavailable panel cannot establish current execution
state. The native status command provides the same evidence:

```sh
soltui call zec.volty.status
```

## Tick learning

The watcher saves every distinct fresh GUM mark it accepts, including marks that
generate no crossing. The private tick database survives a Chrome close or host
restart. Run the read-only worker from the source checkout with Node 22.16 or
newer to learn even while Chrome is closed:

```sh
node extension/tools/zec-volty-learning.mjs --state-dir "$HOME/.soltui/zec-volty"
```

**Tick learning** shows processed marks and trained, pending, expired and
capacity counts for each of the six live-Oracle horizons. The worker uses
the extension's softmax model, price features and frequency baseline. Every
accepted tick still contributes to the feature history. Each horizon keeps
one forecast open at a time and updates only after its endpoint is observed.
An endpoint can arrive up to 10% of the horizon late, capped at 20 seconds.
Missed endpoints expire. The two Brier scores use the same latest 24 resolved
windows, or all resolved windows while there are fewer than 24.

The v2 checkpoint starts a new training run at the worker's first start and
ignores ticks at or before that boundary. The prior checkpoint and raw journal
are retained. Restarts resume the new checkpoint and replay only unprocessed
marks from the same run. Training is shadow-only and measures mark-price
direction. Funded execution follows the separate Volty strategy.

Planning refusals and confirmed preflight refusals before submission record an
allowlisted diagnostic in the execution journal.
An older row with only `gum_plan_unavailable` and no legs proves the planner
stopped before submission. It does not identify which planning check failed.
