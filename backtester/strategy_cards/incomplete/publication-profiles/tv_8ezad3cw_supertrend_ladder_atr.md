---

id: tv_profile_8ezad3cw

name: "Supertrend - Ladder ATR"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Supertrend - Ladder ATR modifies volatility-based trailing stops to avoid widening their distance during an active trend. It argues that favorable large candles should not determine how far a protective stop sits: long positions use volatility from negative candles, while shorts use positive candles. A second restriction accepts a new ATR distance only when it is smaller, producing a tightening ladder. The intended benefit is a closer stop and earlier exit in strong trends. That is a design aim illustrated by the author, not measured improvement or a guarantee against drawdown."

registry_key: null

runner: null

evaluation: null

---

# Supertrend - Ladder ATR

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Supertrend - Ladder ATR modifies volatility-based trailing stops to avoid widening their distance during an active trend. It argues that favorable large candles should not determine how far a protective stop sits: long positions use volatility from negative candles, while shorts use positive candles. A second restriction accepts a new ATR distance only when it is smaller, producing a tightening ladder. The intended benefit is a closer stop and earlier exit in strong trends. That is a design aim illustrated by the author, not measured improvement or a guarantee against drawdown.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Directional ATR sampling/smoothing and the supertrend trail recurrence are unspecified.

- Directional ATR sampling/smoothing and the supertrend trail recurrence are unspecified.

## How it works

- Build direction-specific ATR from red candles for long signals and green candles for short signals.
- During an active trade, ignore increases in the relevant ATR and accept only decreases relative to the prior ATR.
- Apply that distance within a modified supertrend trail.

## Outputs and intended use

- Supertrend direction and a tightened trailing-stop path guide trend-following exits.
- The author contrasts its behavior with conventional ATR-based stops in a USDTRY example.

## Parameters and stated settings

- Settings are described as similar to regular supertrend; no numeric ATR period/multiplier defaults are supplied.

## Failure modes and caveats

- A trail that only tightens its volatility allowance can stop out prematurely after temporary quiet conditions.
- Directional filtering may yield sparse observations or regime-dependent volatility estimates.

## Missing information and implementation boundary

- Exact true-range sampling/smoothing, doji treatment, reset at reversal, multiplier, stop execution and entry conditions are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Directional candles, true ranges and supertrend references can be derived from OHLCV data; exact algorithm remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
ATR derived only based on red candles
```

### E2: mechanism

```text
short trades where using ATR derived from only green candles
```

### E3: mechanism

```text
We will consider the new ATR only if it is lesser than previous bar ATR.
```

### E4: purpose, outputs_and_use

```text
reduce stop loss distance and exit slightly quicker.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8ezad3cw_supertrend_ladder_atr](../tv_8ezad3cw_supertrend_ladder_atr.md)
- [tv_method_atr_trailing](../../tv_method_atr_trailing.md)
- [tv_method_trailing_stop](../../tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/8EZaD3CW-Supertrend-Ladder-ATR/

Publication ID: 8EZaD3CW. Source SHA-256: 51d9e695c40172e9494fca8337114dd3f8647cfb00d5215354ea962646026e68. Raw-description SHA-256: 2064cf04a680b47ee6af0083f372018743e6d85f6002005668b6fc634a706bf6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
