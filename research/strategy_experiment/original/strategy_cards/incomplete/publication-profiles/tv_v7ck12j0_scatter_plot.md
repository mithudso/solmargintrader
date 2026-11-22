---

id: tv_profile_v7ck12j0

name: "Scatter Plot"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Price Volume Scatter Plot retains intrabar price/volume pairs instead of compressing all activity into a conventional profile. It accumulates observations sharing a close price and places volume against price, with a best-fit line for visual relationship context. It is financial distribution analysis even though the legacy tag calls it non-signal; it does not prescribe entries."

registry_key: null

runner: null

evaluation: null

---

# Scatter Plot

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Price Volume Scatter Plot retains intrabar price/volume pairs instead of compressing all activity into a conventional profile. It accumulates observations sharing a close price and places volume against price, with a best-fit line for visual relationship context. It is financial distribution analysis even though the legacy tag calls it non-signal; it does not prescribe entries.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Equal-close intrabar volume scatter is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Read lower-timeframe close/volume observations, aggregate volume at equal close prices and scatter price against accumulated volume.
- Add a regression line, optional profile context and recent largest intrabar-volume labels, adapting placement to the chart viewport.
- Given supplied uncapped LTF observations,group by exactly equal close price;for price p sum volumes of intrabars with close=p and plot that pair(p,sum). Caller selects LTF/sample;regression,auto-LTF rounding and display truncation remain excluded.

## Outputs and intended use

- Inspect participation concentration and how its price location changes; hover for price/volume and watch data-population warnings.
- Usable scope: Equal-close intrabar volume scatter. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Up to five prior maximum-volume values; source describes five hundred boxes plus five hundred labels and warnings beyond one thousand observations or below one hundred bars. Auto multiple defaults 1500.

## Failure modes and caveats

- Analytical: close-based allocation omits within-intrabar distribution, capped drawings can omit data and plan/granularity limitations affect detail.

## Missing information and implementation boundary

- Regression variables/weighting, exact same-price grouping, auto-LTF rounding and truncation selection are not fully specified.

## Data requirements

Required inputs: lower-timeframe close and volume observations.

Repository input-class support: available. Lower-resolution OHLCV supports the data class; actual intrabar history/entitlement and drawing completeness remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to 5 last maximum intrabar volume values
```

### E2: parameters, readiness

```text
500 boxes and 500 labels
```

### E3: parameters, readiness

```text
population size exceeds 1000
```

### E4: parameters, readiness

```text
at least 100 bars
```

### E5: parameters, readiness

```text
1500 (default)
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
One of the scatter plot's advantages is that volumes at the same price level are added to each other.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
The [i]Price Volume Scatter Plot[/i] publication aims to provide intrabar detail as a [url=https://en.wikipedia.org/wiki/Scatter_plot]Scatter Plot[/url].
```

## Source

https://www.tradingview.com/script/v7cK12j0-Scatter-Plot/

Publication ID: v7cK12j0. Source SHA-256: 6e48a0509dac49092bcb5a1ba3748fe4a0156508f3b78fa92438c7a06942b72e. Raw-description SHA-256: 8aaa87fa42bbde5a6b1f22d0d65dac2ce1093708f4ededc58dae8f905cc112ea.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
