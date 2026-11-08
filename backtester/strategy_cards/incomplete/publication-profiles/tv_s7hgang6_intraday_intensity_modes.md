---

id: tv_profile_s7hgang6

name: "Intraday Intensity Modes"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Intraday Intensity Modes applies a price-location/volume pressure concept over complete sessions, accumulated history or rolling normalized windows. It aims to preserve the original day-based interpretation even when plotted on intraday bars, updating the developing day’s OHLCV as new bars arrive. An experimental intrabar option instead measures each chart candle independently. The author suggests combining signs or divergences with Bollinger-band interactions, but does not define a trade strategy. Above daily resolution, the same architecture becomes period intensity rather than literally intraday intensity."

registry_key: null

runner: null

evaluation: null

---

# Intraday Intensity Modes

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Intraday Intensity Modes applies a price-location/volume pressure concept over complete sessions, accumulated history or rolling normalized windows. It aims to preserve the original day-based interpretation even when plotted on intraday bars, updating the developing day’s OHLCV as new bars arrive. An experimental intrabar option instead measures each chart candle independently. The author suggests combining signs or divergences with Bollinger-band interactions, but does not define a trade strategy. Above daily resolution, the same architecture becomes period intensity rather than literally intraday intensity.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The actual intensity equation and rolling session treatment are not provided.

## How it works

- Track developing daily high/low/close/volume on daily-or-lower charts unless intrabar mode is enabled.
- Calculate an undisclosed intensity measure, optionally cumulatively sum it or normalize rolling sums by rolling volume.

## Outputs and intended use

- Independent-session values, open-ended cumulative line or normalized oscillator support pressure/context analysis.

## Parameters and stated settings

- Osc Length 1 disables oscillation; larger values enable II% mode.
- Example normalized oscillator uses 21 days. Cumulative, Normalized, Intrabar and plot style/color controls are supplied.

## Failure modes and caveats

- Developing-session readings change before session close.
- Volume availability is required; experimental per-bar mode departs from the original concept.

## Missing information and implementation boundary

- Base intensity equation, session timezone, exact rolling normalization, defaults and zero-range handling are absent.

## Data requirements

Required inputs: ohlcv, daily session boundaries.

Repository input-class support: available. Session OHLCV aggregation and volume normalization use OHLCV data; exact formula is undisclosed.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
normalized 21 day II% oscillator
```

### E2: parameters

```text
Set to 1 disables oscillation
```

### E3: mechanism, readiness

```text
rolling window of Osc Length values are summed and normalized to the rolling window's volume.
```

### E4: mechanism

```text
tracks the intraday high, low, close and volume for the day
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_s7hgang6_intraday_intensity_modes](../tv_s7hgang6_intraday_intensity_modes.md)

## Source

https://www.tradingview.com/script/S7HGang6-Intraday-Intensity-Modes/

Publication ID: S7HGang6. Source SHA-256: 022f598d4c9186159f98c93a8fb4aa2f1cc9197aad571d23e3bbe50715fba682. Raw-description SHA-256: b6e7e6c45115f6514809dbe012ad4f0ffeea3648a6534c0ba85350946369732e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
