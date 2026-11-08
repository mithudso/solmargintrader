---

id: tv_profile_whfedbdv

name: "Chart Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Chart Oscillator rescales a bounded momentum oscillator into the current price range so it can be viewed directly against candles. It aims to make price-versus-momentum relationships visible without a separate pane. The lower/upper price-channel extremes substitute for oscillator endpoints, while midpoint and overbought/oversold references move with that range. The resulting plotted line is a transformed oscillator, not a tradable price or independent support level. A table preserves the original RSI/Stochastic readings for reference."

registry_key: null

runner: null

evaluation: null

---

# Chart Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Chart Oscillator rescales a bounded momentum oscillator into the current price range so it can be viewed directly against candles. It aims to make price-versus-momentum relationships visible without a separate pane. The lower/upper price-channel extremes substitute for oscillator endpoints, while midpoint and overbought/oversold references move with that range. The resulting plotted line is a transformed oscillator, not a tradable price or independent support level. A table preserves the original RSI/Stochastic readings for reference.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Underlying oscillator settings and exact price mapping/threshold contract are incomplete.

## How it works

- Calculate selected Stochastic or RSI and map its bounded value between rolling lowest low and highest high.
- Derive midpoint and extreme-zone references within that same price-scale interval.

## Outputs and intended use

- On-chart oscillator and channel/reference lines plus raw-value table support visual momentum comparison.

## Parameters and stated settings

- Oscillator choice and range length len are disclosed; periods and overbought/oversold defaults are absent.

## Failure modes and caveats

- Rescaling can create apparent price-level confluence mechanically.
- A shifting range changes visual position even when oscillator value is stable.

## Missing information and implementation boundary

- RSI/Stochastic settings, mapping equation, threshold defaults and signal rules are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Both oscillators and range endpoints are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
lowest(low, len)
- highest(high, len)
```

### E2: parameters

```text
0 and 100
```

### E3: parameters

```text
50 line
```

### E4: outputs_and_use

```text
table is included with the Stoch/RSI values
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_whfedbdv_chart_oscillator](../tv_whfedbdv_chart_oscillator.md)

## Source

https://www.tradingview.com/script/WhfEDBDv-Chart-Oscillator/

Publication ID: WhfEDBDv. Source SHA-256: 39c04c604d9f30d23376a335e73511290baa9e344fbbed2453ccf61457612cec. Raw-description SHA-256: 58eb4ea19167910b59f50725e25a1f784cfb604b3b89ac687592041d6d9e79ff.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
