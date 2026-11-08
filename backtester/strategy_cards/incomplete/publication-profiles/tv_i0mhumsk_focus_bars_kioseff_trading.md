---

id: tv_profile_i0mhumsk

name: "Focus Bars [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Reconstruct recent candles into price-row activity profiles to compare internal participation rather than only final OHLC shape."

registry_key: null

runner: null

evaluation: null

---

# Focus Bars [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Reconstruct recent candles into price-row activity profiles to compare internal participation rather than only final OHLC shape.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The central volume/directional-pressure allocation is unspecified and the finest data contract is not established.

- Directional-volume classification
- Per-row distribution and scaling
- Selected granularity data/retention contract

## How it works

- Sample lower-timeframe observations, divide each parent bar into rows and distribute volume/estimated directional pressure into them. Default width represents total activity; Delta Bars sends signed imbalance in opposite directions. Stack recent reconstructed bars and annotate buy/sell values.

## Outputs and intended use

- Use intensity gradients, labels and side-by-side bars to locate participation concentrations or changing pressure. The author explicitly describes the result as an approximation whose detail depends on the available feed.

## Parameters and stated settings

- Granularity choices are one minute, one second or one tick. Bar count, row resolution, total-volume/delta mode, colors and offset are customizable; numerical defaults are absent.

## Failure modes and caveats

- A finer display does not establish exchange trade-aggressor truth. Different feeds and available lower-history depth can produce different profiles, while tick mode requires event data beyond historical OHLCV.

## Missing information and implementation boundary

- Directional classification, price-volume allocation, row boundaries, scaling and retention rules are not disclosed.

## Data requirements

Required inputs: lower-timeframe OHLCV or tick events.

Repository input-class support: unavailable or unresolved. Minute/second modes could use lower OHLCV, but tick mode and the exact directional allocation require additional unverified data/contracts.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
1-minute
 [*]1-second
 [*]1-tick
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
it is an approximation of internal order flow
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
accuracy depends on available lower timeframe data
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_i0mhumsk_focus_bars_kioseff_trading](../tv_i0mhumsk_focus_bars_kioseff_trading.md)

## Source

https://www.tradingview.com/script/I0MhUmSK-Focus-Bars-Kioseff-Trading/

Publication ID: I0MhUmSK. Source SHA-256: 022316873f52135d171e887a570866b51049c7a72082974c4c82e65062b7594e. Raw-description SHA-256: 793aba95c210dda62d8902f6a0c4dea52b559ec2018df3d60601546a4ff76a99.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
