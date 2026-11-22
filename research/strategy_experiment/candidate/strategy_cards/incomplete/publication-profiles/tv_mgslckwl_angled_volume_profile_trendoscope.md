---

id: tv_profile_mgslckwl

name: "Angled Volume Profile [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Angled Volume Profile extends volume-profile analysis from horizontal price levels to lines with a user-selected slope. It aims to help trendline-oriented traders inspect demand/supply concentration along a trending frame of reference. Interactive start time/price and an ending price determine the angle, while the current last bar bounds the profile history. The description emphasizes user-controlled geometry and rendering constraints rather than an automatic trend detector. It also states that new bars do not update the display automatically, a critical limitation for anyone treating the profile as live context."

registry_key: null

runner: null

evaluation: null

---

# Angled Volume Profile [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Angled Volume Profile extends volume-profile analysis from horizontal price levels to lines with a user-selected slope. It aims to help trendline-oriented traders inspect demand/supply concentration along a trending frame of reference. Interactive start time/price and an ending price determine the angle, while the current last bar bounds the profile history. The description emphasizes user-controlled geometry and rendering constraints rather than an automatic trend detector. It also states that new bars do not update the display automatically, a critical limitation for anyone treating the profile as live context.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Angled price-volume allocation and time/price slope normalization are unspecified.

- Angled price-volume allocation and time/price slope normalization are unspecified.

## How it works

- Use selected start time/price and end price to define the profile’s angle and historical interval.
- Calculate volume levels along that angled frame through the current last bar.
- Space profile lines according to a step multiplier.

## Outputs and intended use

- Angled volume-profile lines provide discretionary trendline-relative participation context.

## Parameters and stated settings

- Interactive start/end geometry, step multiplier, color and style are configurable.
- The source describes a 500-line limit; too-small steps remove lines and too-large steps produce sparse profiles.

## Failure modes and caveats

- The profile becomes stale on new bars until an interactive point is moved.
- User-selected angle can create hindsight bias, and line removal may hide parts of the distribution.

## Missing information and implementation boundary

- Exact volume allocation, slope normalization, bin sizing, defaults and trading rules are absent.

## Data requirements

Required inputs: ohlcv, user-selected profile geometry.

Repository input-class support: unavailable or unresolved. OHLCV supplies prices/volume, but the required manual anchors and slope are not specified for a reproducible run.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Start and End price are used for identifying the angle
```

### E2: mechanism

```text
Last bar of the chart is considered as ending bar.
```

### E3: parameters

```text
Max 500 lines
```

### E4: risks

```text
there will not be visual update when new bars are created.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mgslckwl_angled_volume_profile_trendoscope](../tv_mgslckwl_angled_volume_profile_trendoscope.md)

## Source

https://www.tradingview.com/script/MgsLckWl-Angled-Volume-Profile-Trendoscope/

Publication ID: MgsLckWl. Source SHA-256: 641a3eea87d37d10713ec1dcbf8148bf172e269322e44e340f5f7a480e79c4df. Raw-description SHA-256: 41dddad5b18baffd5696223466695aebdabc2aa48bb9b133fc325848de8fec66.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
