# Oracle leveraged controls and paper forward test

The existing Oracle winner display now opens a separate panel with **L** or the
Leverage button. The panel shows ZEC/BTC venue capabilities, frozen strategy
rules, live Coinbase quotes and the durable paper ledger. It displays the full
public transaction wallet, named CLI key and any configured identity mismatch. Returning to the
original display does not stop the collector.

From the canonical checkout, the monitored view is:

```sh
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py --leverage-panel
```

The original `tui` alias and plain/JSON display modes remain supported. The bar
filter has All, 5, 10, 15 and 20 minute choices. The selected paper rules are
ZEC15m DD/range reversal→UP and BTC20m DD continuation→DOWN. These were selected
on validation data before examining the final split. Both lost under the
historical16bps roundtrip scenario; they are exploratory forward candidates.
The complete study is in `research/REVERSAL-SHAPES.md`.

The panel compares independently timestamped Jupiter Oracle and Coinbase book streams. A silent green/yellow/red dot reports each source’s freshness while the last displayed price remains visible; the basis appears only when both observations meet strict freshness and synchronization checks. Jupiter is the primary display for 1000×. These display quotes do not change the frozen Coinbase paper collector or its selection. The [second-turn study](../research/REVERSAL-SECOND-TURN.md) is retrospective and does not qualify a funded strategy.

## Persistent paper collector

The root-owned tmux session is `oracle-forward-2289`. Its collector window runs:

```sh
cd /Users/mitch/dev/solmargintrader
/Users/mitch/.venvs/soltui/bin/python -m oracle_leverage.forward --home /Users/mitch/.local/state/oracle-leverage --selection /Users/mitch/.local/state/oracle-leverage/selection.json --poll 5
```

The task launches this process and leaves it running. Do not start a duplicate:
the lifetime lock rejects a second collector for the same home. The monitor
window uses the same home. Closing the TUI leaves the collector running.

The collector reads public Coinbase Exchange ZEC-USD/BTC-USD minute candles and
fresh bid/ask midpoint quotes. It records only a new matching current-boundary
setup, at most30seconds late. It commits the decision before the outcome and
never fills missed targets retrospectively. Settlement requires every target
minute, positive volume and a completed target. A missing outcome stays
unscored. One bounded recovery read per asset/minute can recover outcomes from
the preceding24hours. Older missing data stays unavailable.

The ledger is `/Users/mitch/.local/state/oracle-leverage/ledger.sqlite3`.
Selection is hashed and cannot change after observations begin. The collector
never imports the execution adapters and cannot send an order. Paper returns
use the actual observed entry midpoint, the final completed target close and
a16bps roundtrip scenario. They do not include observed Jupiter borrow/funding,
liquidation or venue fills. Historical Binance USDT and prospective Coinbase
USD data have separate identities.

## Multi-timeframe paper observer

The separate MTF observer uses frozen training-only shape models on completed 5, 10, 15 and 20 minute bars. Its own ledger and model live under `/Users/mitch/.local/state/oracle-leverage/mtf`; it does not change the original collector or its selection. Its results use observed Oracle proxy prices, not venue fills. A complete 200ms price path is required for final survival scoring; missing evidence stays unscored. The [retrospective report](../research/MTF-REVERSAL.md) explains the model, selection and limitations.

## Explicit trading controls

The **Arm** control explicitly enables only the selected venue, binds the active public wallet, and sets that venue’s collateral cap from the displayed amount. **Disarm** disables that venue. These actions do not submit an order. **Preview** builds a dry-run request. **Submit preview** is a separate operator action. Fresh installations are disarmed. The paper worker does not call either
operation. A submitted or ambiguous intent remains quarantined until chain and
venue reconciliation establishes its state; a timeout never causes a retry.

The standard10x adapter uses the installed official Jupiter CLI0.10.1, with its
entrypoint SHA256 pinned in `oracle_leverage/cli.py`. It supports BTC here. The
official CLI's JLP markets are BTC/SOL/ETH; ZEC is not one of them. A preview
records the public wallet and named key. Live submission checks that identity,
the private collateral cap, current positions, required quote/fee fields and
the preview lifetime. The named key is passed explicitly without changing the
CLI's global active key. No keys are imported or copied by this feature.

An owner-only0600 configuration at
`/Users/mitch/.local/state/oracle-leverage/config.json` may explicitly set
`armed`, `wallet_address` and `max_collateral_usd`. No configuration is created
to arm trading during the forward test. The wallet must already exist in the
CLI. Funded execution remains unverified in this delivery; all funded tests
use controlled fixtures.

The1000x bridge uses community `jupiter-sdk`0.6.0 and the official public
service at https://yolo-api.jup.ag . The current official app matches the SDK
program, BTC and ZEC market addresses. The backend builds v0 transactions and
co-signs keeper execution after the owner signs. No API key is needed for this
public contract. The implementation accepts direct JupUSD collateral only;
fund the existing wallet with JupUSD and enough SOL for network fees.

The SDK verifies the requested margin,1000x leverage, direction, market, owner,
keeper, funding account, known config/pool/vault/position PDAs and execution
window before signing. The service supplies a close claim address; the on-chain
program validates its allocation, rather than this client deriving an unverified
claim sequence. It
rejects unknown extra instructions and priority fees above0.01SOL. The existing
pinned CLI signs with the explicit named wallet; private keys never enter this
module. A second check verifies the owner signature cryptographically and keeps
the message and keeper signature slot unchanged. The ledger records the owner
signature before sending to the keeper. Processing means queued, not filled.

To permit manual1000x execution, the private configuration must also contain
`"sdk": {"enabled": true}`. A configuration example is:

```json
{"armed": true, "wallet_address": "YOUR_EXISTING_PUBLIC_WALLET", "max_collateral_usd": 10, "sdk": {"enabled": true}}
```

The Arm control creates or updates this private configuration only after an explicit operator action. Submit refreshes and verifies
the reviewed economic intent because the service's execution window starts at
build time. Close verifies the current owned position, its trigger/timer state
and the minimum15second hold. SDK positions have a1000x prefix to preserve venue
identity. The pending execution queue and unpaid-profit queue are distinct.

The public frontend contract and source hashes are recorded in
`docs/ORACLE-JUPITER-1000X-CONTRACT.md`. Offline fixtures cover signing and keeper
responses. Funded execution is not claimed from those tests or an unsigned
preview. Existing wallet balance may prevent the venue simulation/build.

## Verification

```sh
cd /Users/mitch/dev/solmargintrader
/Users/mitch/.venvs/soltui/bin/python -W error::ResourceWarning -m unittest oracle_leverage.tests.test_console oracle_leverage.tests.test_forward oracle_leverage.tests.test_market oracle_leverage.tests.test_process_adapters research.tests.test_reversal_shapes research.tests.test_zec_leverage_panel
cd /Users/mitch/dev/solmargintrader/oracle_leverage/sdk
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

These checks cover actual loopback HTTP and child processes, causal rules,
durable decisions, no-backfill restarts, UI workers and real SDK construction.
They do not establish funded execution or future profitability.

Official CLI reference: https://github.com/jup-ag/cli/blob/main/docs/perps.md

Product execution rules: https://docs.jup.ag/user-docs/trade/1000x/trading

Community SDK: https://github.com/ChiefWoods/jupiter-sdk
