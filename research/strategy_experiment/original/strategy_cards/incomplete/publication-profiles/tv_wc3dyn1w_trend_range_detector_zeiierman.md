---

id: tv_profile_wc3dyn1w

name: "Trend Range Detector (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Detect sustained price compression around a movement-weighted center and color subsequent breaks from the resulting range."

registry_key: null

runner: null

evaluation: null

---

# Trend Range Detector (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Detect sustained price compression around a movement-weighted center and color subsequent breaks from the resulting range.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The envelope scale is supplied, but custom center weighting and box lifecycle/breach rules remain unspecified.

- Exact speed-weighted center equation
- Range bounds/merging
- Touch versus close breakout rule

## How it works

- Weight closes more heavily when their bar-to-bar changes are larger. Require recent closes to remain within an envelope based on ATR of two thousand bars times a configurable factor, then draw a range box.

## Outputs and intended use

- Blue boxes denote consolidation, green upper breaks and red lower breaks. Use them with separate momentum/volume/trend evidence; the display does not establish that accumulation or distribution actually occurred.

## Parameters and stated settings

- Minimum Range Length, Range Width Multiplier and Highlight Box Breaks are inputs. Numerical length/multiplier defaults are not listed.

## Failure modes and caveats

- A very long ATR baseline reacts slowly to changing volatility. A developing bar can cross and return inside a range; instant coloring is not necessarily a confirmed closing breakout.

## Missing information and implementation boundary

- Exact speed weighting, zero-change handling, box boundaries/merging and breach-price criteria are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class; code parity and cached-history coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Based on an ATR(2000) multiplied by a user-defined factor
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bars with higher momentum (larger price differences between closes) are given more weight.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
maximum distance between all recent closes and a dynamic centerline
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_wc3dyn1w_trend_range_detector_zeiierman](../tv_wc3dyn1w_trend_range_detector_zeiierman.md)

## Source

https://www.tradingview.com/script/WC3DYn1W-Trend-Range-Detector-Zeiierman/

Publication ID: WC3DYn1W. Source SHA-256: e6091851804594152255b91c7e2b215c124beaa9a2015f080d7b86d8848a5e59. Raw-description SHA-256: 189e15cac6187c798dd5af1b44c9bfa78ecb503a1d64e27b85994aa49679f12d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
