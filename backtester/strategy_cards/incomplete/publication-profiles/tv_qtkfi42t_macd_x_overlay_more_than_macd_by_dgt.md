---

id: tv_profile_qtkfi42t

name: "MACD-X Overlay, More Than MACD by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare several MACD-style transformations as an oscillator projected onto the price chart."

registry_key: null

runner: null

evaluation: null

---

# MACD-X Overlay, More Than MACD by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare several MACD-style transformations as an oscillator projected onto the price chart.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The traditional idea is known, but core custom variants and overlay/time-confirmation contracts are undisclosed.

- Leader/Source variant equations
- Overlay scaling
- Early/confirmed cross conditions

## How it works

- Offer conventional fast-minus-slow averages, histogram-as-source, a weighted MACD Leader and the author's Source/MA interpretation. Each variant changes the signal line/histogram, while the overlay adapts to linear/log display and raises early or confirmed line-cross alerts.

## Outputs and intended use

- Use signal crosses, zero crosses and divergence as familiar momentum context. The author explains zero crossings as underlying fast/slow average crosses and warns about false positives/negatives.

## Parameters and stated settings

- Overlay retains up to250 bars. The histogram discussion uses a nine-day EMA signal; actual fast/slow defaults, custom-variant settings and chart scaling are not listed.

## Failure modes and caveats

- Leading or earlier crosses can also increase noise and are not evidence of improved returns. Divergence or positive oscillator values can persist without a reversal/entry opportunity.

## Missing information and implementation boundary

- Leader weights, ambiguous Source/MA formula, overlay scaling, signal smoothing and early-versus-confirmed timing are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed features use OHLCV; missing custom calculations are specification gaps, not missing raw market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Maximum plotting length is limited to 250 bars
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
the 9-day EMA of MACD
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
MACD-AS (Histogram), MACD-Leader and MACD-Source
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
both for Early Warning and Confirmed Crossovers
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_qtkfi42t_macd_x_overlay_more_than_macd_by_dgt](../tv_qtkfi42t_macd_x_overlay_more_than_macd_by_dgt.md)

## Source

https://www.tradingview.com/script/qtkFi42t-MACD-X-Overlay-More-Than-MACD-by-DGT/

Publication ID: qtkFi42t. Source SHA-256: 268f158a4983876cbcb194eab064a682a8eec7fb04e0c0f2c49a9c51f7118d0c. Raw-description SHA-256: 51a5aa8674b13d89769661da9a58bd467456abb85a0a7a356bfccc6a0c8c2513.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
