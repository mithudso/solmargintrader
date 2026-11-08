---

id: tv_profile_psnjpa2y

name: "VWAP Price Channel"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "VWAP Price Channel replaces the flat corners of a Donchian channel with VWAP-derived paths anchored at new channel extremes. It is explicitly a thought experiment, implemented as a trend-flipping trail rather than a proven predictive model. The idea is to let price and volume update a reference while the underlying Donchian boundary remains flat. New opposite-side VWAPs during a trend may be read as continuation-breakout references, but they are not themselves trend changes. The author warns higher-timeframe live and historical calculations naturally differ."

registry_key: null

runner: null

evaluation: null

---

# VWAP Price Channel

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

VWAP Price Channel replaces the flat corners of a Donchian channel with VWAP-derived paths anchored at new channel extremes. It is explicitly a thought experiment, implemented as a trend-flipping trail rather than a proven predictive model. The idea is to let price and volume update a reference while the underlying Donchian boundary remains flat. New opposite-side VWAPs during a trend may be read as continuation-breakout references, but they are not themselves trend changes. The author warns higher-timeframe live and historical calculations naturally differ.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for raw high/low-source anchored VWAP references reset at new Donchian extrema for a selected window. The adjusted trail, simultaneous-extreme state ordering and HTF live/historical parity remain outside this scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent raw references: for a chosen Donchian lookback detect new rolling highs/lows. Re-anchor the upper built-in VWAP using that new-high candle high as source, and the lower VWAP using the new-low candle low as source. Between respective anchor events each is the volume-weighted average of its high/low source since its anchor; these raw references are distinct from the adjusted Start+Change trail.
- Set trend direction from newly formed highs/lows and display the relevant trail.
- When raw VWAP lags farther from price than the Donchian boundary, shift the start reference and add subsequent VWAP changes to it.

## Outputs and intended use

- VWAP-derived trail, price-to-trail fill and opposite-side levels support experimental trend/continuation inspection.

## Parameters and stated settings

- No Donchian length, timeframe or numeric trail defaults are disclosed.
- Raw-reference scope takes a chosen Donchian lookback; no numeric default is supplied. High and low VWAP streams reset at their respective new-extreme events; simultaneous-event ordering remains unspecified.

## Failure modes and caveats

- Adjusted start-plus-change path is not always true anchored VWAP.
- Live/historical higher-timeframe discrepancies undermine naive historical signal assumptions.
- A visually anticipatory curve does not establish forecasting ability.

## Missing information and implementation boundary

- Exact start-reference adjustment, simultaneous-extreme handling, reversal/stop trigger, defaults and execution rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Donchian extrema and volume-weighted price calculations use OHLCV; precise live aggregation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, risks

```text
serves solely as a thought experiment.
```

### E2: mechanism, readiness

```text
new highs or lows from the DC
```

### E3: mechanism

```text
VWAP change is added to the new (closer to price) DC value.
```

### E4: risks

```text
natural calculation discrepancy when using live data vs. historical.
```

### E5: mechanism, readiness

```text
detecting new highs or lows from the DC and using those as the anchor frequency on the built-in VWAP function.
```

### E6: mechanism, readiness

```text
So each time a new high or low is made based on DC, the VWAP function re-anchors to the high or low of the candle.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)
- [tv_psnjpa2y_vwap_price_channel](../tv_psnjpa2y_vwap_price_channel.md)

## Source

https://www.tradingview.com/script/Psnjpa2Y-VWAP-Price-Channel/

Publication ID: Psnjpa2Y. Source SHA-256: c2df4ff935ad35d5d6d8688a26edcb061c40a6eef7d2d47a308950bf2984f651. Raw-description SHA-256: 437dff1199b131eb833fb451c291bfaa6862022ebfa9e39bc32a36541a1187b3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
