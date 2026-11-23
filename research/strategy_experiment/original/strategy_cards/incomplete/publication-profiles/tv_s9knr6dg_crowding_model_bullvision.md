---

id: tv_profile_s9knr6dg

name: " Crowding model ║ BullVision"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Crowding Model places cryptocurrencies on an RSI-versus-price-Z-score map to show momentum alongside historical extension. It summarizes groups with sentiment-style labels and highlights extreme zones, giving the user a relative market snapshot. “Crowding” is a metaphor inferred from price behavior here; the source does not use actual holdings, leverage concentration or participant positioning."

registry_key: null

runner: null

evaluation: null

---

# Crowding model ║ BullVision

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Crowding Model places cryptocurrencies on an RSI-versus-price-Z-score map to show momentum alongside historical extension. It summarizes groups with sentiment-style labels and highlights extreme zones, giving the user a relative market snapshot. “Crowding” is a metaphor inferred from price behavior here; the source does not use actual holdings, leverage concentration or participant positioning.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Per-asset RSI/Z-score scatter is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Compute RSI for momentum and price deviation from a historical average in Z-score units, then scatter assets on those axes.
- Classify quadrants by high/low RSI and positive/negative Z-score and summarize asset distributions into FOMO, Fear, Recovery and Strength categories.
- For caller price/windows, use standard RSI(length) and Z=(price-rolling_mean(price,N))/rolling_std(price,N) as coordinates. Require adequate history/nonzero scale and explicit caller variance convention. Categories/aggregate benchmarks/alerts remain outside scope.

## Outputs and intended use

- Inspect clusters, benchmark positions and danger zones for context; source explicitly gives no buy/sell signals.
- Usable scope: Per-asset RSI/Z-score scatter. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Inputs include RSI length, Z-score lookback, crowding-alert sensitivity, scale, benchmark visibility and panel/labels; no numeric defaults or exact quadrant cutoffs are supplied.

## Failure modes and caveats

- Analytical: price extension and momentum do not measure actual crowded positioning, and extreme readings can persist.

## Missing information and implementation boundary

- Symbol universe, normalization details, thresholds, category aggregation and alert rules are not specified.

## Data requirements

Required inputs: selected cryptocurrency price histories, benchmark/aggregate crypto series.

Repository input-class support: unavailable or unresolved. Requires multiple selected assets and aggregate-market feeds; no complete or point-in-time universe is supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
positioning each cryptocurrency according to its RSI and Z-score.
```

### E2: outputs_and_use, readiness

```text
This indicator does not provide explicit buy or sell signals.
```

### E3: outputs_and_use, readiness

```text
FOMO (Fear of Missing Out): High momentum, potential exhaustion.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
[i][b]📊 RSI and Z-Score Analysis[/b][/i]
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
The Crypto Crowding Model Pro is a sophisticated analytical tool designed to visualize and quantify market conditions across multiple cryptocurrencies. By leveraging Relative Strength Index (RSI) and Z-score calculations, this indicator provides traders with an intuitive and detailed snapshot of current crypto market dynamics, highlighting areas of extreme momentum, crowded trades, and potential reversal points.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_s9knr6dg_crowding_model_bullvision](../tv_s9knr6dg_crowding_model_bullvision.md)

## Source

https://www.tradingview.com/script/S9KNr6dG-Crowding-model-BullVision/

Publication ID: S9KNr6dG. Source SHA-256: 6f62caf694710cc8aed500aa0e9b579316a31534f48cec6ac10fb4eee7f502d3. Raw-description SHA-256: ed5a6ce3902d43186cbaaf1a3518d48b06b07691dee3edd5456fb78e93e5494e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
