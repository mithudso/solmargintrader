---

id: tv_profile_uive2izt

name: "Harmonic Patterns Based Trend Follower"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Harmonic Patterns Based Trend Follower uses recognized harmonic structures to define breakout-like directional boundaries. Instead of treating a harmonic completion automatically as a reversal entry, it takes the pattern’s highest point as bullish threshold and lowest as bearish threshold. Reaching either changes the trend state, which otherwise persists. New patterns replace the boundaries. The source deliberately uses confirmed pivots, accepting delayed recognition. The resulting method is a trend-state overlay derived from pattern geometry, not a fully disclosed harmonic detector or executable strategy."

registry_key: null

runner: null

evaluation: null

---

# Harmonic Patterns Based Trend Follower

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Harmonic Patterns Based Trend Follower uses recognized harmonic structures to define breakout-like directional boundaries. Instead of treating a harmonic completion automatically as a reversal entry, it takes the pattern’s highest point as bullish threshold and lowest as bearish threshold. Reaching either changes the trend state, which otherwise persists. New patterns replace the boundaries. The source deliberately uses confirmed pivots, accepting delayed recognition. The resulting method is a trend-state overlay derived from pattern geometry, not a fully disclosed harmonic detector or executable strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core zigzag and harmonic-recognition rules are undisclosed.

## How it works

- Build zigzag and scan the latest five confirmed pivots for harmonic patterns.
- Set detected-pattern maximum/minimum as bullish/bearish zones.
- Switch trend when price touches a boundary; retain prior direction otherwise and update zones on new patterns.

## Outputs and intended use

- Blue pattern lines, green/red boundaries, trend-colored bars and signed trend value support directional monitoring.

## Parameters and stated settings

- Trend output is +1/-1; pattern-specific selection is not exposed.
- Source mentions 500-line drawing limit and deletion of old patterns.

## Failure modes and caveats

- Confirmed-pivot delay means pattern origins predate detection.
- Pattern names and included ratio families are hidden, limiting interpretability.

## Missing information and implementation boundary

- Zigzag settings, harmonic ratio rules, zone-touch price, simultaneous-touch ordering, initialization and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Pattern pivots and boundary comparisons are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism

```text
last 5 confirmed pivots
```

### E2: mechanism, readiness

```text
highest point of pattern will become the bullish zone
```

### E3: mechanism

```text
lower point of the pattern will become bearish zone.
```

### E4: parameters

```text
Trend value can be 1 or -1
```

### E5: parameters

```text
max 500 lines
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)
- [tv_uive2izt_harmonic_patterns_based_trend_follower](../tv_uive2izt_harmonic_patterns_based_trend_follower.md)

## Source

https://www.tradingview.com/script/UivE2izt-Harmonic-Patterns-Based-Trend-Follower/

Publication ID: UivE2izt. Source SHA-256: 924f3614d70264aeb14f26b94f94f3f16df6cee16a275c5d0c919763518df36c. Raw-description SHA-256: 845e210e30995fe5f2754478e2edb35ff9305d19098b63eaacef39f6aaca806b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
