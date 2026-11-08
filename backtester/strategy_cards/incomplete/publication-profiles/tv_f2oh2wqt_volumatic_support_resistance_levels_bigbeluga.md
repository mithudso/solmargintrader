---

id: tv_profile_f2oh2wqt

name: "Volumatic Support/Resistance Levels [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volumatic Support/Resistance Levels adds volume emphasis to swing-based price zones. It aims to distinguish ordinary structural levels from areas associated with stronger participation, using histogram-like fills and high-volume marks. The author suggests those emphasized zones as context for possible reversals or breakouts alongside other structure tools. This is a reactive visualization of price pivots and volume, not direct evidence that particular participants defended a level or a complete order-block algorithm."

registry_key: null

runner: null

evaluation: null

---

# Volumatic Support/Resistance Levels [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volumatic Support/Resistance Levels adds volume emphasis to swing-based price zones. It aims to distinguish ordinary structural levels from areas associated with stronger participation, using histogram-like fills and high-volume marks. The author suggests those emphasized zones as context for possible reversals or breakouts alongside other structure tools. This is a reactive visualization of price pivots and volume, not direct evidence that particular participants defended a level or a complete order-block algorithm.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pivot confirmation, volume-percentile calculation and zone geometry are absent.

- Pivot confirmation, volume-percentile calculation and zone geometry are absent.

## How it works

- Detect recent pivot highs as resistance and lows as support using a configurable range.
- Wrap levels in bands whose width/intensity vary with percentile volume.
- Mark zone edges and color bars when volume exceeds a configured threshold.

## Outputs and intended use

- Red resistance/green support zones, dynamic fills, circles and orange high-volume candles show structural and activity context.

## Parameters and stated settings

- Range length, volume threshold, sensitivity and colors are configurable; numeric defaults are not disclosed.

## Failure modes and caveats

- Pivot confirmation may delay levels and ongoing volume changes may alter their appearance.
- High volume can accompany either acceptance or rejection and does not establish conviction or direction.

## Missing information and implementation boundary

- Pivot confirmation rule, percentile window, band geometry, threshold units, level invalidation and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Pivot prices, candle volume and percentile comparisons are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
pivot-based resistance (highs)
```

### E2: mechanism

```text
support (lows)
```

### E3: mechanism

```text
expand/contract based on percentile volume.
```

### E4: parameters, mechanism

```text
volume > user-defined threshold
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_f2oh2wqt_volumatic_support_resistance_levels_bigbeluga](../tv_f2oh2wqt_volumatic_support_resistance_levels_bigbeluga.md)
- [tv_method_order_blocks](../tv_method_order_blocks.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/F2OH2WQT-Volumatic-Support-Resistance-Levels-BigBeluga/

Publication ID: F2OH2WQT. Source SHA-256: 920588f0aac2ce1d00947798c510f653923ec0f6b9e966b72112160d03e03bc2. Raw-description SHA-256: a6593ec4608c604f779a908ba06d5044bf84d5ce088915215e50e39d58b42076.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
