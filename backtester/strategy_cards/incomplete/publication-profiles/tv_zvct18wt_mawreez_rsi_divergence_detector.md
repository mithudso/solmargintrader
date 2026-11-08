---

id: tv_profile_zvct18wt

name: "Mawreez' RSI Divergence Detector"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Mawreez RSI Divergence Detector represents divergence strength continuously instead of marking only a few selected pivot pairs. It sums valid divergences of regular and hidden types, using opposite slopes between price and RSI and requiring connecting lines not to cross their underlying series. The author explicitly distinguishes larger divergence magnitude from a higher chance of a successful reversal."

registry_key: null

runner: null

evaluation: null

---

# Mawreez' RSI Divergence Detector

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Mawreez RSI Divergence Detector represents divergence strength continuously instead of marking only a few selected pivot pairs. It sums valid divergences of regular and hidden types, using opposite slopes between price and RSI and requiring connecting lines not to cross their underlying series. The author explicitly distinguishes larger divergence magnitude from a higher chance of a successful reversal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The exact magnitude metric, handling of overlapping/types with opposing signs and line-intersection tolerance are not supplied.

- The exact magnitude metric, handling of overlapping/types with opposing signs and line-intersection tolerance are not supplied.

## How it works

- Search candidate divergence lengths, compare source/RSI line slopes and reject lines crossing the corresponding series.
- Accumulate magnitudes of valid regular and hidden divergences into a histogram, colored by divergence type.

## Outputs and intended use

- Inspect current developing divergence and type-specific colors; unfinished divergences can invalidate or grow through more drives.

## Parameters and stated settings

- RSI default length 14; divergence length defaults minimum 3, maximum 28. Colors distinguish bullish, bearish and hidden variants.

## Failure modes and caveats

- Author warns developing divergences can invalidate or grow; magnitude does not establish likelihood of playing out.

## Missing information and implementation boundary

- The exact magnitude metric, handling of overlapping/types with opposing signs and line-intersection tolerance are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
default length: 14
```

### E2: parameters, readiness

```text
minimum length 3 and maximum length 28
```

### E3: mechanism, readiness

```text
The slopes of said lines must have opposite signs
```

### E4: mechanism, readiness

```text
Said lines may not cross their respective series.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_method_rsi_divergence](../../tv_method_rsi_divergence.md)
- [tv_zvct18wt_mawreez_rsi_divergence_detector](../tv_zvct18wt_mawreez_rsi_divergence_detector.md)

## Source

https://www.tradingview.com/script/ZVCT18Wt-Mawreez-RSI-Divergence-Detector/

Publication ID: ZVCT18Wt. Source SHA-256: e3b36142e2d0a068a0ee2b27b176fe5e12ae3b4af02b6bd6a71aa12752f87d46. Raw-description SHA-256: 7a9f51967062aec54165b9d4f1a932fdfc811d54f324b4c6876a0f87b2e4cad3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
