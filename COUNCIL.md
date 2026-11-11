# Council paper bot

Open **Bot monitor → Council** in the extension, or **Bots → Council** in SolTUI.
Save settings, then press **Start paper Council**. The detached worker continues
after either interface closes. **Stop Council** cancels unfilled decisions and
pauses monitoring; it retains any open paper position for the next start.

The bot uses the same current vote eligibility as Live signals: both the strategy
record and contributed horizon must meet the accuracy and resolved-sample floors.
Expired predictions cannot vote. Each strategy contributes equal weight.

| Current position | Council action |
| --- | --- |
| Flat | Open long at Strong Buy (score ≥60). |
| Long | Hold until Sell (score ≤−20), then close. |
| Flat, shorts enabled | Open short at Strong Sell (score ≤−60). |
| Short | Hold until Buy (score ≥20), then close. |
| Either side, strong opposite signal | Close; reverse only when shorting and confidence permit the new side. |
| Votes unavailable | Hold; request prediction recovery. |

Defaults are paper only, 1×, long only, 60% accuracy, 20 resolved outcomes per
horizon, and a separate 0.80 entry-confidence floor. Shorting and leverage require
their explicit settings. Agreement strength is not success probability. Council
builds confidence from at least 20 prospectively recorded one-minute outcomes;
it can remain flat while warming up. Risk-reducing exits bypass entry confidence.
Changing settings requires a stopped bot with no open position or pending fill.

The bot freezes source votes, expiry, eligibility policy and code revision when
observed. It uses real, contiguous Coinbase one-minute candles for paper fills
and marks the Jupiter USD price as a reference. A fill uses the first minute open
strictly after the decision, confirmed after that real bar closes. Entries must
still have eligible evidence at fill time. Missing candles are never filled in.
These are proxy simulations, not Jupiter execution or liquidity quotes.

The shared Jupiter Perps simulation charges 6 bps fees plus 2 bps slippage per
side, with configured borrow rates and collateral liquidation. These assumptions
are configurable through `council.config`; they are not measured venue fills.
The bot records observations, confidence outcomes and fills under the configured
SolTUI directory's `council/`. No wallet, signing or venue-order API is called.

The shared registry exposes `council.config`, `council.start`, `council.stop` and
`council.status` on all four SolTUI surfaces. `forwardtest.health` reads prediction
producer state; `forwardtest.ensure` starts or requests work from the single shared
paper producer. An explicit prediction Stop pauses automatic recovery until Start.
The unavailable alert links to **Forward testing** and offers **Start predictions**
when the producer is stopped. Fresh quotes alone do not establish fresh predictions.
