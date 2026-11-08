---

id: tv_profile_xgnuhodo

name: "Open Interest Chart [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Open Interest Chart renders changes in selected futures COT open interest as circular spikes or rings. It is a compact multi-market activity display whose geometry is primarily a visualization technique. Rising OI is not literal net money flow or participant direction by itself, and the report’s weekly publication frequency remains distinct from the chart/request timeframe."

registry_key: null

runner: null

evaluation: null

---

# Open Interest Chart [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Open Interest Chart renders changes in selected futures COT open interest as circular spikes or rings. It is a compact multi-market activity display whose geometry is primarily a visualization technique. Rising OI is not literal net money flow or participant direction by itself, and the report’s weekly publication frequency remains distinct from the chart/request timeframe.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Percentage-change lag, missing/revised report handling, exact ticker defaults and value-to-radius scaling are not fully specified.

- Percentage-change lag, missing/revised report handling, exact ticker defaults and value-to-radius scaling are not fully specified.

## How it works

- Retrieve selected open-interest series, calculate percentage changes and map positive/negative values into circular drawing positions/colors.
- Reposition plots when the visible chart range changes so the circular display remains near the right edge.

## Outputs and intended use

- Compare OI changes across selected markets, reading green/red/blue/gray for positive/negative/zero/missing data.

## Parameters and stated settings

- Up to six tickers; request timeframe defaults Daily, while COT data is weekly. From-middle rendering is on by default; size, angle, labels and colors are configurable.

## Failure modes and caveats

- Drawing between bars is approximate and replay can be slow; analytical: OI increase does not identify bullish versus bearish exposure or an actual capital-flow amount.

## Missing information and implementation boundary

- Percentage-change lag, missing/revised report handling, exact ticker defaults and value-to-radius scaling are not fully specified.

## Data requirements

Required inputs: selected COT futures open-interest histories.

Repository input-class support: unavailable or unresolved. External COT report series and market mappings are required; OHLCV does not contain OI.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to 6 different Futures Open interest tickers
```

### E2: parameters, readiness

```text
Default set TF is Daily
```

### E3: parameters, readiness

```text
published weekly
```

### E4: parameters, readiness

```text
Enabled (default): Drawings start from the middle circle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_xgnuhodo_open_interest_chart_luxalgo](../tv_xgnuhodo_open_interest_chart_luxalgo.md)

## Source

https://www.tradingview.com/script/xGnUhodO-Open-Interest-Chart-LuxAlgo/

Publication ID: xGnUhodO. Source SHA-256: 2df8a92273af59e59f92bfb5cfc8f95b7494d3cc27bc3cb6e467ef161b502439. Raw-description SHA-256: b7e060861cdfe000acc8a0fcec66723336c810a4563df7f491a7eb5b46548062.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
