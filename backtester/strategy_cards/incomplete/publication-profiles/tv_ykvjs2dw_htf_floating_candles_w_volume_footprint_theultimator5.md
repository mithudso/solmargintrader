---

id: tv_profile_ykvjs2dw

name: "HTF Floating Candles w/ Volume Footprint [theUltimator5]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "HTF Floating Candles places developing higher-timeframe candles beside the working chart and adds footprint volume rows across their range. It aims to preserve broader price/volume context without obscuring lower-timeframe action. The source distinguishes its footprint-request data from a whole-candle direction heuristic, but that author assertion is not an independent audit of the feed’s trade-side construction."

registry_key: null

runner: null

evaluation: null

---

# HTF Floating Candles w/ Volume Footprint [theUltimator5]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

HTF Floating Candles places developing higher-timeframe candles beside the working chart and adds footprint volume rows across their range. It aims to preserve broader price/volume context without obscuring lower-timeframe action. The source distinguishes its footprint-request data from a whole-candle direction heuristic, but that author assertion is not an independent audit of the feed’s trade-side construction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Selected-timeframe floating candles is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Request footprint information, display selected HTF candles to the right and aggregate row-wise buy/sell volume over the displayed range.
- Arrange volume on opposite sides or stacked on the left and optionally extend historical high/low location lines backward.
- Render caller-selected HTF OHLC candles with open-close bodies and low-high wicks;display caller count1–10. Supplied timestamps define positions;footprint data,aggregation and live-request parity excluded.

## Outputs and intended use

- Use the view as visualization support rather than a standalone signal; the active HTF candle updates until completion.
- Usable scope: Selected-timeframe floating candles. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Default candle count is one, maximum ten. Controls include timeframe, position/size, row count/width, layout, colors and high/low lines.

## Failure modes and caveats

- Analytical: developing HTF values change, multi-candle profiles aggregate across their combined range, and platform access may differ from historical entitlement wording.

## Missing information and implementation boundary

- Footprint row aggregation, feed-side semantics, HTF confirmation, request settings and default row granularity are absent.

## Data requirements

Required inputs: HTF OHLC, platform footprint buy/sell volume rows.

Repository input-class support: unavailable or unresolved. Requires footprint data unavailable from ordinary OHLCV; platform entitlement and feed coverage are unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
default number of HTF candles is 1, but you can add up to 10
```

### E2: mechanism, readiness

```text
request.footprint()
```

### E3: mechanism, readiness

```text
volume profile of the entire plotted HTF candle range.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Instead of forcing you to mentally reconstruct the most recent daily (or weekly/monthly) candle(s) while watching lower-timeframe price action, this script draws floating HTF candles to the right side of the chart and updates it live as the higher-timeframe bar develops.  The default number of HTF candles is 1, but you can add up to 10 HTF candles.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
This indicator is designed to pull higher-timeframe candles outside of the chart, and add the footprint volume data to give a complete snapshot of the Higher Timeframe (HTF) trading range and volume data without cluttering your view.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_footprint](../tv_method_volume_footprint.md)
- [tv_ykvjs2dw_htf_floating_candles_w_volume_footprint_theultimator5](../tv_ykvjs2dw_htf_floating_candles_w_volume_footprint_theultimator5.md)

## Source

https://www.tradingview.com/script/ykVjs2dW-HTF-Floating-Candles-w-Volume-Footprint-theUltimator5/

Publication ID: ykVjs2dW. Source SHA-256: c192bd786129eba3f93ebfafb0a2fa1b0e45f86aa872a66b4c24c6ff1b9a38e9. Raw-description SHA-256: 38ec1a372f7d18af851ea4023e22ab0e673007cef6cbce240ec1e6ebc698f5fa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
