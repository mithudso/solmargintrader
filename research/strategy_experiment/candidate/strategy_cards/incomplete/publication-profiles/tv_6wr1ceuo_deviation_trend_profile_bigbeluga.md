---

id: tv_profile_6wr1ceuo

name: "Deviation Trend Profile [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Deviation Trend Profile studies how closes are distributed around a moving average during an identified trend phase. It combines slope-based trend changes with a price-frequency histogram, aiming to distinguish strong directional occupation of outer zones from contraction near the mean. The author suggests following outer-zone persistence and becoming cautious or considering a fade when the profile contracts. Although the source calls these statistical deviation zones, it explicitly constructs them using ATR; that difference matters because the bands should not be read as conventional standard-deviation probability intervals. The author labels the tool experimental and educational."

registry_key: null

runner: null

evaluation: null

---

# Deviation Trend Profile [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Deviation Trend Profile studies how closes are distributed around a moving average during an identified trend phase. It combines slope-based trend changes with a price-frequency histogram, aiming to distinguish strong directional occupation of outer zones from contraction near the mean. The author suggests following outer-zone persistence and becoming cautious or considering a fade when the profile contracts. Although the source calls these statistical deviation zones, it explicitly constructs them using ATR; that difference matters because the bands should not be read as conventional standard-deviation probability intervals. The author labels the tool experimental and educational.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The slope measure, trend-state reset and histogram-bin construction are undefined.

- The slope measure, trend-state reset and histogram-bin construction are undefined.

## How it works

- Detect trend changes when SMA slope exceeds a signed threshold.
- Build ATR-based envelopes around the SMA and count closes within bins during the active trend phase.
- Update trend markers, SMA color and duration labels alongside the distribution.

## Outputs and intended use

- Colored circles mark bullish/bearish starts; an SMA gradient shows direction.
- A histogram, trend-duration label and outer-zone lines describe persistence and concentration.

## Parameters and stated settings

- Slope threshold is ±0.1; band labels are ±1, ±2 and ±3.
- Bins Amount changes distribution granularity; source gives no SMA/ATR length defaults.

## Failure modes and caveats

- ATR envelopes are not standard-deviation bands despite the source terminology.
- Threshold units and slope normalization are unspecified, limiting cross-instrument interpretation.
- Trend-shift entries and discretionary fading lack disclosed stops or position sizing.

## Missing information and implementation boundary

- Exact slope calculation, ATR multiplier convention, trend reset/bin boundaries, default lengths and complete execution rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed SMA, ATR and close-frequency components use OHLCV data; unavailable formula details remain algorithm gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
slope of the SMA exceeds a ±0.1 threshold.
```

### E2: mechanism, parameters, risks

```text
Calculates ±1, ±2, and ±3 levels from the SMA using ATR
```

### E3: mechanism, outputs_and_use

```text
how often price closed within each deviation zone during the active trend phase.
```

### E4: purpose, risks

```text
experimental indicator
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6wr1ceuo_deviation_trend_profile_bigbeluga](../tv_6wr1ceuo_deviation_trend_profile_bigbeluga.md)

## Source

https://www.tradingview.com/script/6Wr1CEuo-Deviation-Trend-Profile-BigBeluga/

Publication ID: 6Wr1CEuo. Source SHA-256: 5a8aa8dd9e1e51b8118bc2eaa2d8f5351f509f140989fa0282cd174dc6344212. Raw-description SHA-256: fce0e62f4c0059f7e1ec6afa1c503d377c2e5f5f808b3d087b82cfc61d2e97ac.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
