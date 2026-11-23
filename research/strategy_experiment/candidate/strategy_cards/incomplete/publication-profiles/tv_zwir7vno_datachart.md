---

id: tv_profile_zwir7vno

name: "DataChart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "DataChart renders sample distributions as scatterplots or heatmaps and includes a price-event displacement interface. That explicit event-price component makes it a financial research library even though its chart machinery also accepts generic samples. It aims to help callers inspect the distribution and quadrant counts of outcomes after chosen events. The caller supplies triggers and data, while chart properties control scaling and outlier presentation. The interface alone does not establish what constitutes a favorable event or a predictive signal."

registry_key: null

runner: null

evaluation: null

---

# DataChart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

DataChart renders sample distributions as scatterplots or heatmaps and includes a price-event displacement interface. That explicit event-price component makes it a financial research library even though its chart machinery also accepts generic samples. It aims to help callers inspect the distribution and quadrant counts of outcomes after chosen events. The caller supplies triggers and data, while chart properties control scaling and outlier presentation. The interface alone does not establish what constitutes a favorable event or a predictive signal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Price-event displacement equations and outcome timing are not specified.

## How it works

- Collect x/y samples when a trigger is true and render them through a chart object.
- A specialized price-sample path derives event-driven displacement using configured duration and ATR/percentage reference.
- Filter extreme percentiles or place outliers in border cells; optionally share x/y scale.

## Outputs and intended use

- Scatterplot/heatmap, quadrant counts, tooltips and title support distributional event research.

## Parameters and stated settings

- Defaults: scatterplot, trigger true, price close/high/low and true range; ATR reference true, common scale false.
- Duration, ATR length, matrix size, outlier percentiles, formatting and visual properties are configurable.

## Failure modes and caveats

- Outlier removal can conceal tail risk; border accumulation changes how tails appear.
- Event selection can introduce hindsight bias.

## Missing information and implementation boundary

- Exact displacement x/y definitions, look-forward timing, ATR calculation, percentile/binning conventions and defaults are absent.

## Data requirements

Required inputs: ohlcv, caller event triggers and configuration.

Repository input-class support: unavailable or unresolved. OHLCV supplies prices/ranges, but the required event and displacement contract is caller-defined and not supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, readiness

```text
special type of sample designed to measure price displacements of events
```

### E2: parameters

```text
duration[/b]: impact duration
```

### E3: parameters

```text
useAtrReference[/b]: Default is true.
```

### E4: parameters

```text
Default is set to false.
```

### E5: parameters

```text
Default is close
```

## Source

https://www.tradingview.com/script/ZWIR7vNo-DataChart/

Publication ID: ZWIR7vNo. Source SHA-256: ed1d363e0a287902bbf2ae6a9a5c68188b27b133f8f161eeda646e3c87f97a3b. Raw-description SHA-256: ee14fef21a535b4dfb74d6eae43390f6f0a2ba4b346d7da86058eee1cfba27ba.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
