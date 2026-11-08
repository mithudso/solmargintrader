---

id: tv_profile_xyaiqwd8

name: "Auto Trendline Indicator (based on fractals)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Auto Trendline connects recently detected fractals to make trendline placement systematic. Its aim is to reduce discretionary drawing bias by using a consistent pivot-selection process. Crossing markers can highlight price interaction with the resulting lines, but the author explicitly treats the lines as references rather than evidence that slope predicts future direction. The publication describes the broad fractal confirmation concept while leaving the exact line and crossing predicates incomplete."

registry_key: null

runner: null

evaluation: null

---

# Auto Trendline Indicator (based on fractals)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Auto Trendline connects recently detected fractals to make trendline placement systematic. Its aim is to reduce discretionary drawing bias by using a consistent pivot-selection process. Crossing markers can highlight price interaction with the resulting lines, but the author explicitly treats the lines as references rather than evidence that slope predicts future direction. The publication describes the broad fractal confirmation concept while leaving the exact line and crossing predicates incomplete.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain unresolved.

- Fractal period convention, pivot pairing and crossing predicates are incomplete.

## How it works

- Identify local high/low fractals using a configurable surrounding-bar period.
- Connect the most recent fractals into trendlines and optionally retain historical lines.
- Place a configurable marker at detected crossings.

## Outputs and intended use

- Use drawn lines as price references within another analysis process.
- Customize colors, extension direction, historical visibility and crossing-symbol display.

## Parameters and stated settings

- The traditional fractal value mentioned is 5; the crossing marker defaults to X.

## Failure modes and caveats

- Longer confirmation periods increase lag.
- Historical pivot placement can obscure the delay before a line became available.

## Missing information and implementation boundary

- Whether period counts each side or total width, equality handling, same-type pivot pairing and close/wick crossing rules are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
connecting the most recent fractals.
```

### E2: parameters

```text
default symbol “X”
```

### E3: parameters

```text
Traditionally, chartists pick the value of 5.
```

### E4: risks

```text
it will take more bars to confirm the printed fractal.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_xyaiqwd8_auto_trendline_indicator_based_on_fractals](../../tv_xyaiqwd8_auto_trendline_indicator_based_on_fractals.md)

## Source

https://www.tradingview.com/script/xYaiqwD8-Auto-Trendline-Indicator-based-on-fractals/

Publication ID: xYaiqwD8. Source SHA-256: 89a3e29815b3736fed2f575bf708d5751d45dbb471e50cc9eeda2278dbe44978. Raw-description SHA-256: 7bde94b285c8a5a1612444c9651c51906572fdcfc705bc2c285c9468a6518180.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
