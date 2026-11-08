---

id: tv_profile_ls42zpse

name: "72s: Adaptive Hull Moving Average+"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Adaptive Hull Moving Average+ varies its smoothing period with either volume or volatility and colors the resulting curve according to trend direction and slope. Its purpose is to distinguish relatively inactive conditions from stronger movement while preserving a moving-average support/resistance reference. The author positions it as a companion to other analysis and offers discretionary entries combining price location, curve color and RSI. These examples do not establish measured profitability or a fully defined execution policy."

registry_key: null

runner: null

evaluation: null

---

# 72s: Adaptive Hull Moving Average+

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Adaptive Hull Moving Average+ varies its smoothing period with either volume or volatility and colors the resulting curve according to trend direction and slope. Its purpose is to distinguish relatively inactive conditions from stronger movement while preserving a moving-average support/resistance reference. The author positions it as a companion to other analysis and offers discretionary entries combining price location, curve color and RSI. These examples do not establish measured profitability or a fully defined execution policy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the named fixed-period WMA HMA curve with integer component lengths, obtained by equal period bounds. Adaptive volume/volatility lengths, colors and alerts remain incomplete.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow fixed HMA mode sets Minimum Period=Maximum Period=N. Expand the named WMA-based Hull construction as HMA_N(X)=WMA_(int(sqrt(N)))(2×WMA_(int(N/2))(X)−WMA_N(X)); integer conversion replaces rounding of component lengths as disclosed. This is the fixed curve only, not the opaque adaptive charger or color logic.
- Construct the HMA from weighted averages with integer conversion rather than rounding of component lengths.
- Lengthen the adaptive period when the chosen activity measure is weak and shorten it when activity strengthens.
- Combine slope with activity state: yellow denotes flat conditions, light directional colors weakness and darker colors stronger movement.

## Outputs and intended use

- Use the colored average and optional background for market-condition assessment.
- A suggested long has price above the average, dark green color and RSI above 50; short is the inverse. Equal minimum and maximum lengths recover a fixed-period curve.

## Parameters and stated settings

- The author example spans 172 to 233 around HMA 200, particularly on 15-minute charts.
- Charger type, period bounds, consolidation threshold and background are configurable.
- Choose a source series and period N with positive integer component lengths; set both period bounds to N. The source gives no source/default fixed-N contract beyond its examples.

## Failure modes and caveats

- Tuning on attractive historical trades can overfit; adaptive smoothing still responds with delay.

## Missing information and implementation boundary

- Volume/volatility normalization, adaptation equation, slope threshold scale, RSI length and exact exits are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the stated input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
172 - 233 is just my own setting to outmatch the static HMA 200 for intraday.
```

### E2: outputs_and_use

```text
3. RSI is above 50. This is to help as additional confirmation.
```

### E3: mechanism, parameters, readiness

```text
using plain int() instead of round() on its wma's length
```

### E4: mechanism

```text
dynamically lengthen the lookback period
```

### E5: mechanism, parameters, readiness

```text
simply put the same value for minimum and maximum period settings, and there you have the original HMA with extra features.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ls42zpse_72s_adaptive_hull_moving_average](../tv_ls42zpse_72s_adaptive_hull_moving_average.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/ls42zPSE-72s-Adaptive-Hull-Moving-Average/

Publication ID: ls42zPSE. Source SHA-256: e2bad28bc9491b95a9260e74d829abff631c99b1868de7d2cf52147479d00ea8. Raw-description SHA-256: 8ca5149a1e3c39ead005062ba01864915ba69559086507ff99c1f193e9f63a97.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
