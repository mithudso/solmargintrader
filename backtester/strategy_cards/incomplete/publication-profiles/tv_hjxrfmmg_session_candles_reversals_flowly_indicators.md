---

id: tv_profile_hjxrfmmg

name: "Session candles & reversals / Flowly Indicators"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Session Candles & Reversals rebuilds candles around trading sessions, detects wick/engulfing reversals relative to the previous corresponding session, and reports historical conditional outcomes. It aims to reveal session-specific directional changes obscured by ordinary daily bars. Its statistics measure next-corresponding-session behavior, not a complete executable strategy. The author recommends using reversals with support/resistance and broader context, while checking sample size. Overlapping sessions and differing market hours make careful session alignment central to the interpretation."

registry_key: null

runner: null

evaluation: null

---

# Session candles & reversals / Flowly Indicators

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Session Candles & Reversals rebuilds candles around trading sessions, detects wick/engulfing reversals relative to the previous corresponding session, and reports historical conditional outcomes. It aims to reveal session-specific directional changes obscured by ordinary daily bars. Its statistics measure next-corresponding-session behavior, not a complete executable strategy. The author recommends using reversals with support/resistance and broader context, while checking sample size. Overlapping sessions and differing market hours make careful session alignment central to the interpretation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Session OHLC aggregation, four reversal inequalities, next-corresponding-session success and magnitude denominators are explicitly defined. Missing portfolio trade rules are irrelevant to this indicator/statistics specification.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Aggregate session OHLC and compare each session with its own prior occurrence.
- Compare extremes with the previous corresponding session, not the immediately preceding different session. Wick-up requires lower high and lower low, close at least 65% up the session low-to-high range and open at least 40%. Wick-down requires higher high and higher low, close at most 35% and open at most 60%. Engulfing-up requires higher high and lower low with close at least 65%; engulfing-down requires higher high and lower low with close at most 35%.
- A reversal succeeds only if the next corresponding session closes higher for an up reversal or lower for a down reversal than the reversal close. Win rate is successful count divided by all reversal count. For successful up/down events, measure favorable percentage excursion from reversal close to next corresponding high/low, sum those excursions and divide by total reversal count (including failures). An optional selected-session moving average is separate.

## Outputs and intended use

- Session candles, reversal labels, historical win-rate/magnitude table, optional validation drawings and session MA support analysis.

## Parameters and stated settings

- UTC defaults: London 08–17, New York 13–22, Sydney 21–06 and Tokyo 00–09.
- Up reversals require close at least 65% of range; down at most 35%. Wick opens require at least 40% or at most 60%, respectively.
- MA supports SMA/EMA/HMA/WMA/RMA and session selection. Recommended chart interval is at most 1H; clearer object drawings cover 500 bars.

## Failure modes and caveats

- Magnitude is accumulated for successful events but divided by total reversal count, so it is not simply average winner excursion.
- Session samples can be small, overlapping and regime-dependent; metrics omit execution costs.
- Misaligned intervals or nontrading session hours cause incorrect/absent candles.

## Missing information and implementation boundary

- Default MA length, statistic sample limits, exact missing-session handling, fill/stop rules and out-of-sample validation are absent.

## Data requirements

Required inputs: intraday ohlcv aligned with configured sessions, session/timezone definitions.

Repository input-class support: unavailable or unresolved. Exact session boundaries require compatible intraday history; chart-history depth and coverage are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
London (08:00 - 17:00, UTC)
```

### E2: parameters

```text
New York (13:00 - 22:00, UTC)
```

### E3: parameters

```text
Sydney (21:00 - 06:00, UTC)
```

### E4: parameters

```text
Tokyo (00:00 - 09:00, UTC)
```

### E5: parameters

```text
close >= 65%
```

### E6: parameters

```text
open >= 40%
```

### E7: parameters

```text
close <= 35%
```

### E8: parameters

```text
open <= 60%
```

### E9: parameters

```text
at or below 1H
```

### E10: parameters

```text
first 500 bars
```

### E11: mechanism, risks, readiness

```text
dividing all percentage increases/decreases with total reversal count
```

### E12: mechanism, parameters, readiness

```text
Wick up:
Lower high, lower low, close >= 65% of session range (0% being the very low, 100% being the very high) and open >= 40% of session range.
```

### E13: mechanism, parameters, readiness

```text
Wick down:
Higher high, higher low, close <= 35% of session range and open <= 60% of session range.
```

### E14: mechanism, parameters, readiness

```text
Engulfing up:
Higher high, lower low, close >= 65% of session range.
```

### E15: mechanism, parameters, readiness

```text
Engulfing down:
Higher high, lower low, close <= 35% of session range.
```

### E16: mechanism, readiness

```text
relative to prior NY session
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hjxrfmmg_session_candles_reversals_flowly_indicators](../../tv_hjxrfmmg_session_candles_reversals_flowly_indicators.md)
- [tv_method_engulfing](../../tv_method_engulfing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/HjXrfMMg-Session-candles-reversals-Flowly-Indicators/

Publication ID: HjXrfMMg. Source SHA-256: 3b5da599baaad8793ad81aed99f8417f10923be27fcf63a96f5e4369a80f31af. Raw-description SHA-256: 93196de2ec4fbce38e1dc006733e8b65969d86f44f557eaa1a820c00c44a1d09.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
