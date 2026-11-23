---

id: tv_profile_beczr3nb

name: "Buyers & Sellers Profile + Dynamic S/R (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Buyers & Sellers Profile + Dynamic S/R refines confirmed swing levels using nearby volume-profile evidence. It aims to combine structural pivots with actual historical participation proxies instead of drawing every swing. Candle volume is distributed by price-range overlap and split by closing location, explicitly as an estimate rather than true footprint data. A nearby profile node can pull a pivot-derived level toward stronger participation, while a second score incorporates candle absorption/rejection. The result supports discretionary retest monitoring, not proof of institutional buying or guaranteed support."

registry_key: null

runner: null

evaluation: null

---

# Buyers & Sellers Profile + Dynamic S/R (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Buyers & Sellers Profile + Dynamic S/R refines confirmed swing levels using nearby volume-profile evidence. It aims to combine structural pivots with actual historical participation proxies instead of drawing every swing. Candle volume is distributed by price-range overlap and split by closing location, explicitly as an estimate rather than true footprint data. A nearby profile node can pull a pivot-derived level toward stronger participation, while a second score incorporates candle absorption/rejection. The result supports discretionary retest monitoring, not proof of institutional buying or guaranteed support.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Proportional overlap and buyShare are disclosed, but no source rule defines the profile row-domain endpoints/boundaries. Adding caller-supplied row intervals would extend the source input contract; a complete rolling profile/POC is therefore still incomplete.

- The rolling profile price-domain endpoints and row-boundary construction are unspecified.
- Zero-range candle allocation is unspecified.

## How it works

- For a nonzero-range candle, buyShare=(Close−Low)/(High−Low), sellShare=1−buyShare. For a defined profile row interval [a,b], the stated proportional overlap allocation corresponds to Volume×max(0,min(High,b)−max(Low,a))/(High−Low), then multiply by the respective shares. Sum row volume over the lookback and choose the maximum-volume row as POC. The source does not define the actual row-domain endpoints, equal-spacing rule or zero-range allocation; this formula therefore describes allocation conditional on rows, not a fully specified published profile.
- Search around confirmed pivots in ATR distance and score node strength, local prominence, directional volume and proximity.
- Blend raw pivot toward chosen node, score profile/absorption/volume/wick evidence, merge nearby same-side levels and invalidate on buffered closes.

## Outputs and intended use

- Rolling split profile, POC and scored support/resistance lines show participation-confirmed structure.

## Parameters and stated settings

- Profile evidence weights 50/20/20/10%; final score weights 50/20/15/15%.
- Lookback/rows, swing length, search/min-node/evidence/pull/score, level cap, merge and break ATR are inputs; defaults absent.

## Failure modes and caveats

- Closing-location allocation is an estimate and zero-range candles require handling.
- Confirmed pivots and historical profile reconstruction must use information available at evaluation time.

## Missing information and implementation boundary

- Subscore normalization, pull-strength mapping, absorption equation, ATR defaults and merge policy are absent.
- The profile price-domain endpoints and row-boundary spacing are not stated; Rows only controls their number. Zero-range candles and maximum-row ties also lack conventions.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The specified profile and structural inputs derive from OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
buyShare = (close - low) / (high - low)
```

### E2: parameters

```text
50% Node Strength

• 20% Local Peak Quality
• 20% Directional Volume
• 10% Pivot Proximity
```

### E3: parameters

```text
50% Profile Evidence

• 20% Absorption
• 15% Pivot Volume
• 15% Wick Rejection
```

### E4: mechanism, readiness

```text
Final Level = Raw Pivot + (Profile Node - Raw Pivot) × Profile Pull
```

### E5: mechanism, readiness

```text
each candle's volume is distributed across the profile rows touched by its high-to-low range. The amount allocated to each row depends on how much of the candle overlaps that price area.
```

### E6: missing_information, readiness

```text
Controls the number of price levels used to divide the profile.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_beczr3nb_buyers_sellers_profile_dynamic_s_r_zeiierman](../tv_beczr3nb_buyers_sellers_profile_dynamic_s_r_zeiierman.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/bEcZR3nB-Buyers-Sellers-Profile-Dynamic-S-R-Zeiierman/

Publication ID: bEcZR3nB. Source SHA-256: 96bba1ab3aae23cd5fbeafdd9d8ca2aceb712e6a1ba20495528ad2ac9616ad08. Raw-description SHA-256: c412edc7fdd323c02d37809171d3be916ba8b9f037aaf9e2ed9d74012fd53ced.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
