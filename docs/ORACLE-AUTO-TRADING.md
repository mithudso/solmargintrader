# Oracle automatic trading and paper mode

Version: 1.1.0
Delta: document optional private shared-owner routing and its activation boundary.

## Controls

Extension0.11.0 adds **Auto Long / Short** to the Jupiter chart panel. The Oracle
TUI exposes the same controls in **Margin / trading**. Both surfaces call the
existing SolTUI command registry and control one private, exclusive session.
Start in one surface and inspect or stop the same session in the other.
Closing either interface does not stop the session.

- **Start Paper** uses simulated execution on genuine observed Jupiter prices.
- **Start Live** requires explicit positive base collateral, maximum collateral
  and session-loss limits, confirmation and complete backend execution readiness.
  The present backend refuses automatic live opening for the reasons below.
- **Stop entries** prevents another entry and manages an open position through a
  terminal outcome. It does not abandon an at-risk position. An unknown paper
  outcome requires an explicit acknowledgement before the session can end.

The asset and venue select BTC or ZEC and the10x or1000x paper product. Initial
paper defaults are10USDC collateral,15USDC maximum collateral and50USDC session
loss reserve. These are engineering defaults for simulation, not live authority.
A session freezes its policy; changes apply to the next session.

Start records a900-second first-entry deadline. Fresh, correctly identified
execution observations after Start determine a causal Long/Short decision.
A short bounded warmup or explicit cold-start fallback prevents waiting forever
for a high confidence score. A missing, stale or invalid execution source causes
a visible operational failure. The deadline never authorizes an invented price.

The existing display feed switches control the older comparison interface.
They do not disable the separate execution monitor while this session is at risk.

## Shared owner routing

Every client uses `ORACLE_AUTOTRADE_HOME` when it is explicitly set. Otherwise it
reads `~/.config/oracle-autotrade/connection.json` if present, and falls back to
`~/.local/state/oracle-autotrade` if the route is absent. The route has exactly
these fields, with an absolute `state_home`:

```json
{"version": 1, "state_home": "/absolute/path/to/existing/owner-state"}
```

The route directory must be owner-only, and the route must be a private,
owner-owned regular file with one link. Symbolic links, oversized files, invalid
JSON and invalid schema fail closed before the client creates state or starts an
owner. An explicit environment override takes precedence even when the route is
invalid. All ordinary clients and the owner they start must run the routing-aware
version; an older client or a client with an override can use another namespace.

Creating or changing a route is a separate operator action. Routing does not move
or merge journals, stop an existing owner, fence concurrent starts, or update a
native-host wrapper. Do not change it while clients or an owner may act without
a maintenance fence. Preserve and verify all journal, request and cohort history
before any separately authorized transition.

## Entry, exit and accounting

Before opening, the owner saves an immutable intent containing direction,
reference price, simulated entry fill, target, stop, liquidation boundary, sizing,
cost assumptions and model/policy identity. It allows one position at a time.
Both paper models target50% modeled net return on collateral, use a15-second
minimum hold, a10-second simulated close delay and a900-second maximum hold.
The owner continues checking received observations during the close delay.
A threshold crossing requests closure; it does not guarantee the final return.

The10x model uses linear isolated exposure, adverse5bps fills,5bps fees per side
on notional and modeled1bp/hour borrow. Its adverse stop is4% from entry, or
approximately40% of collateral before costs. Its liquidation proxy is a10%
adverse price move. This is a synthetic exposure model; it is not a verified
Jupiter10x quote or account liquidation calculation. ZEC is not an available
standard Jupiter CLI perpetual market.

The1000x model reuses the saved frontend's integer nonlinear payout calculation
from `oracle_leverage/exit50.py`, including its close/win-fee and liquidation
rules. It separately declares modeled open costs,0.1bp adverse fills and
0.01bp/hour borrow assumptions. The stop lies halfway from its simulated entry
to the calculated liquidation boundary. This model is versioned separately from
the original frozen Exit50 research cohort; no old research row is relabeled.

The monitor consumes every received execution tick. Touching the liquidation
boundary is a failed trade, including during a pending close. An observation
gap over2seconds, disconnect, invalid basis or out-of-order data makes an
at-risk result unknown. Restarting the owner also preserves an unresolved
position as unknown. Unknown results never count as profitable trades or train
a successful label.

This is an **observed-price-path simulation**. Providers can coalesce updates;
unpublished movements cannot be reconstructed. Entry latency is modeled as zero.
Network, keeper, collateral conversion and unverified venue costs are excluded.
The1000x frontend simulation and a modeled10-second delay do not establish
actual execution, guaranteed closure or continuous liquidation survival.

## Learning, confidence and bounded exposure

The six existing chart learners continue training their independent1m/5m/10m/
15m/20m/1h UP-versus-NONUP targets. Their directional scores do not measure
survival to exit or profit after costs. The Chrome surface may send a fresh,
source-bound stored forecast to the session owner as an advisory input.

The owner has a separate prospective logistic learner for the selected
position's modeled net outcome. It scores the issued forecast before learning
from the later resolved outcome. Liquidation and losing trades train negative
labels; integrity failures stay outside that outcome denominator. Results remain
partitioned by asset, product, leverage and the entire frozen policy/cost cohort.
Paper history never supplies live performance evidence.

A score of75% alone cannot raise exposure. The bounded paper boost also requires
at least100 prospective outcomes for the selected side,30 high-score outcomes,
positive cohort and session net results, prequential Brier/reliability checks,
a Wilson lower-bound check, limited drawdown and no integrity failure. Eligible
paper positions use at most1.5times base collateral, within the explicit maximum
and conservative loss reserve; cooldown falls from30seconds to15seconds.
These fixed engineering gates do not establish a calibrated75% probability or
a validated future trading edge. Liquidation, losses, unknowns and paused periods
remain visible. Unprofitable aggregate outcomes, repeated losses, insufficient
reserve or integrity failures prevent further automatic entries.

## Optional private Anthropic advice

Advice defaults off. If enabled, the owner reads `ANTHROPIC_API_KEY` from its
private process environment when needed. It sends only numeric price/momentum
facts to the fixed Anthropic endpoint, with at most two small calls per session
and a3-second socket timeout. Tests use mocked responses; no real API call was
needed to verify the feature. There is no browser key field or secret logging.

Advice may suggest Long, Short or neutral. It cannot change prices, amounts,
limits, transaction checks or the entry deadline. Late results are discarded.
An in-flight HTTP call cannot be forcibly cancelled; terminal cleanup runs apart
from IPC and refuses a new session until the old resources have retired.
This feature does not give the model a general web browser or signing tool.

## Live readiness

Automatic live entries currently refuse before signing or sending:

- **Standard10x:** the console's CLI response does not establish the required
  owner/market/side/request binding, executed fill, complete fees and terminal
  net settlement. A submitted signature is not a filled position. BTC is the
  only standard10x asset exposed by this console; ZEC is unsupported there.
- **1000x:** the current SDK opening verifier does not establish the matching
  close instruction, debt-queue handling, beneficiary and final payout. The
  standard Perpetuals IDL does not prove the separate experimental product.

Explicit live limits are required in addition to these technical contracts.
The application does not silently fall back to another venue or claim a funded
trade from a paper result. The existing separately armed manual paths retain
their own capabilities and restrictions.

## Runtime and verification

Research-runtime0.4.3 includes `oracle_leverage` with the native host. Its wheel
and self-contained source distribution are tested outside the repository.
The owner uses private local SQLite state and a Unix socket under
`/Users/mitch/.local/state/oracle-autotrade` by default. Request IDs are durable;
retrying an ambiguous UI response uses the same identity. Only one owner can
hold the process lock. Native origin checks and the existing HTTP Origin refusal
remain in force. Model weights and feature vectors stay private to the owner.

The existing monitor entry point remains:

```bash
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py
```

Focused source verification uses the installed test environment:

```bash
INDEX_NO_AUTO=1 /Users/mitch/.venvs/soltui/bin/python -m unittest oracle_leverage.tests.test_autotrade_engine soltui.tests.test_autotrade_registry research.tests.test_zec_leverage_panel research.tests.test_zec_feed_controls
INDEX_NO_AUTO=1 npm --prefix /Users/mitch/dev/solmargintrader/extension test
```

Source tests, packaging imports, installed native messaging and genuine-price
paper execution are separate gates. None establishes a profitable strategy or
verified funded execution. Exact delivery and installed acceptance receipts are
recorded in the versioned continuation log.
