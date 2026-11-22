---

id: tv_profile_qeqcsffc

name: "Dekidaka-Ashi - Candles And Volume Teaming Up (Again)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dekidaka-Ashi overlays volume-sensitive price envelopes without replacing the underlying candle shape. It aims to combine candle body movement and relative volume in a price-scaled display, enabling derived bands and experimental breakout labels. The author explicitly doubts signal accuracy and observes that signals often occur in low-volume/low-volatility conditions. This is a financial visualization and research concept, not a validated predictor. Its volume scaling depends only on current and preceding volume rather than a rolling maximum, although that design choice alone does not prove all non-repainting behavior."

registry_key: null

runner: null

evaluation: null

---

# Dekidaka-Ashi - Candles And Volume Teaming Up (Again)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dekidaka-Ashi overlays volume-sensitive price envelopes without replacing the underlying candle shape. It aims to combine candle body movement and relative volume in a price-scaled display, enabling derived bands and experimental breakout labels. The author explicitly doubts signal accuracy and observes that signals often occur in low-volume/low-volatility conditions. This is a financial visualization and research concept, not a validated predictor. Its volume scaling depends only on current and preceding volume rather than a rolling maximum, although that design choice alone does not prove all non-repainting behavior.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the unsmoothed high/low envelope from current/(current+previous) volume, absolute candle body and chosen amplitude multiplier. Zero-volume policy, optional smoothing and breakout reference indexing remain limitations.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Unsmoothed raw-envelope scope: q_t=Volume_t/(Volume_t+Volume_(t−1)), using the current and preceding candle volume. A zero denominator requires an explicit caller policy; none is supplied.
- Let B_t=|Close_t−Open_t| and k be the chosen body-size amplitude multiplier. Compute D_t=k×q_t×B_t, DekidakaHigh_t=High_t+D_t and DekidakaLow_t=Low_t−D_t. This describes the raw volume-rescaled envelope; optional volume smoothing and breakout indexing are excluded.
- Optionally smooth volume; average derived bounds to form bands and classify high/low crosses by candle direction.

## Outputs and intended use

- Overlay envelope bodies, optional bands and strong/weak bullish/bearish or two-sided-uncertain labels support exploratory breakout reading.

## Parameters and stated settings

- Body size, smoothing and Show signals are inputs.
- Examples compare body size 2 versus 1, smoothing 100 and bands with MA length/body size 20.
- Narrow scope uses unsmoothed volume and a caller-selected body-size multiplier. The source compares body sizes 1 and 2 but supplies no exact default or smoothing-off numeric setting.

## Failure modes and caveats

- The author says accuracy needs study and low-activity signals may be undesirable.
- Zero total volume and ambiguous crossing references require explicit handling.

## Missing information and implementation boundary

- Smoothing type, exact signal reference/current-versus-prior bound, default settings and zero-volume policy are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All disclosed scaling and signals use candle prices and volume.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
volume is divided by the sum between the current volume value and the precedent volume value
```

### E2: mechanism

```text
multiplied by the absolute close/open difference
```

### E3: parameters

```text
body with size 2, in red with size 1.
```

### E4: parameters

```text
smooth = 100.
```

### E5: parameters

```text
period 20 and the body size equal to 20.
```

### E6: risks

```text
not confident at all on their accuracy
```

### E7: mechanism, readiness

```text
this result is multiplied by the absolute close/open difference and added/subtracted to the high/low price.
```

### E8: parameters, mechanism, readiness

```text
body size setting, with higher values increasing the body amplitude.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)
- [tv_method_renko](../tv_method_renko.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_qeqcsffc_dekidaka_ashi_candles_and_volume_teaming_up_again](../tv_qeqcsffc_dekidaka_ashi_candles_and_volume_teaming_up_again.md)

## Source

https://www.tradingview.com/script/QeqcSffc-Dekidaka-Ashi-Candles-And-Volume-Teaming-Up-Again/

Publication ID: QeqcSffc. Source SHA-256: ad96275519fd670599a92681786ebc9dc0467d5e33e634e96ed1cbee141be9a1. Raw-description SHA-256: 31381267b6ee61f65e994b57389c48d54c0c8f2707a6203920bba72b61a1831f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
