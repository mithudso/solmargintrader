---

id: tv_profile_sxgyrede

name: "Dynamic Swing Anchored VWAP (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dynamic Swing Anchored VWAP resets its reference at newly confirmed swings and weights recent observations more strongly through decay. It is intended to remain closer to current structure than a long cumulative anchored VWAP, making pullbacks and retests easier to inspect. The volatility-aware speed adjustment is a responsiveness choice rather than evidence that this reference is more trustworthy or a uniquely correct fair value."

registry_key: null

runner: null

evaluation: null

---

# Dynamic Swing Anchored VWAP (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dynamic Swing Anchored VWAP resets its reference at newly confirmed swings and weights recent observations more strongly through decay. It is intended to remain closer to current structure than a long cumulative anchored VWAP, making pullbacks and retests easier to inspect. The volatility-aware speed adjustment is a responsiveness choice rather than evidence that this reference is more trustworthy or a uniquely correct fair value.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Swing confirmation, price/volume decay and ATR-adaptation equations are absent.

- Swing confirmation, price/volume decay and ATR-adaptation equations are absent.

## How it works

- Confirm swing highs/lows with the Swing Period and begin a new anchored average when market direction flips.
- Compute decayed price-times-volume averaging from the anchor; optionally modify tracking speed using ATR relative to average ATR.

## Outputs and intended use

- Use the line as a swing-relative value guide for trend pullbacks or discretionary mean-reversion analysis.

## Parameters and stated settings

- Swing Period, Adaptive Price Tracking in bars, ATR-ratio adaptation and Volatility Bias are configurable. Bias above 1 strengthens adaptation and below 1 weakens it; no defaults are given.

## Failure modes and caveats

- Analytical: pivot confirmation delays anchoring and adaptive decay differs from conventional cumulative VWAP; apparent pivot-origin lines may conceal availability timing.

## Missing information and implementation boundary

- Pivot confirmation details, decay equations, ATR windows, anchor backfill and numeric defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
new pivot confirmed
```

### E2: mechanism, readiness

```text
VWAP is computed using a decay model
```

### E3: parameters, readiness

```text
>1 = stronger effect; <1 = lighter touch.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_sxgyrede_dynamic_swing_anchored_vwap_zeiierman](../tv_sxgyrede_dynamic_swing_anchored_vwap_zeiierman.md)

## Source

https://www.tradingview.com/script/SxgyrEde-Dynamic-Swing-Anchored-VWAP-Zeiierman/

Publication ID: SxgyrEde. Source SHA-256: 93d7b3ae0c61d924bbd0f2bb8e5957c85cffcd6befbe2f8dba80ee14f2834bf4. Raw-description SHA-256: efc5f912a2732b7d2752b6023bba6a1e3ab260b06dd5d622c86f72a01f504c73.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
