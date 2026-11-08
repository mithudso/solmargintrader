---

id: tv_profile_ifjxxalc

name: "The Investment Clock Orbital Graph"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Place economic growth and inflation in a quadrant-based investment-clock chart to frame broad asset-allocation hypotheses."

registry_key: null

runner: null

evaluation: null

---

# The Investment Clock Orbital Graph

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Place economic growth and inflation in a quadrant-based investment-clock chart to frame broad asset-allocation hypotheses.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for four-quadrant classification of supplied growth/inflation rates against caller thresholds; obtaining those rates and exact orbital rendering remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Given supplied GDP-growth and CPI-inflation rates, compare each against the caller-selected sustainable-growth/inflation threshold. High growth/high inflation maps to Overheating; low growth/high inflation to Stagflation; high growth/low inflation to Recovery; low growth/low inflation to Reflation.
- Plot rate pairs and their historical trail as an orbital-style scatter view. The source names FRED but does not specify exact rate transformations, series identifiers or historical release-vintage alignment.

## Outputs and intended use

- Use the current quadrant and path to discuss macro conditions. The author favors commodities/energy in overheating, defensive assets in stagflation, growth stocks in recovery and bonds/value/financials in reflation; these are heuristic suggestions, not verified return forecasts.

## Parameters and stated settings

- Growth/inflation thresholds, trail length and scatter resolution are adjustable. Numeric defaults and specific FRED series are not provided.

## Failure modes and caveats

- GDP and inflation have different reporting lags and revisions. A chart using revised history is not a real-time historical forecast, and regime-to-asset relationships can change.

## Missing information and implementation boundary

- Country/series identifiers, growth transformations, release-date alignment, revision vintages, smoothing and executable allocation rules are absent.

## Data requirements

Required inputs: FRED GDP growth and CPI histories, release timestamps and revision vintages.

Repository input-class support: unavailable or unresolved. Macroeconomic series and their publication timing are external requirements not supplied by OHLCV or the description.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
dynamic scatter plot of GDP growth vs. CPI inflation rates.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Utilizes FRED (Federal Reserve Economic Data)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Set sustainable GDP growth and inflation thresholds, adjust trail length
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Overheating (High Growth, High Inflation)
```

### E5: mechanism, parameters, readiness

```text
1)🔥 Overheating (High Growth, High Inflation)
     2)📉 Stagflation (Low Growth, High Inflation)
     3)🤒 Recovery (High Growth, Low Inflation)
     4)🎈 Reflation (Low Growth, Low Inflation)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ifjxxalc_the_investment_clock_orbital_graph](../tv_ifjxxalc_the_investment_clock_orbital_graph.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/ifjXxAlC-The-Investment-Clock-Orbital-Graph/

Publication ID: ifjXxAlC. Source SHA-256: c14eead51e8aef0ecc63e9a9a4e81e1019b55a61e6668ca176b9d44aa20003e4. Raw-description SHA-256: d5fc6075eab548c70105695df9143d96973c18b08a0ffc106a2c55624bf94843.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
