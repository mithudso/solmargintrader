---

id: tv_profile_e9l1xaqd

name: "Support Resistance MTF"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Support Resistance MTF derives higher-timeframe price references directly and uses them to draw support/resistance zones on the working chart. The author emphasizes that the higher-timeframe OHLC values are calculated without a security call. Users can choose wick extremes or body prices and adjust local-extreme sensitivity, so the levels represent a configurable view of higher-interval structure rather than a single fixed market definition."

registry_key: null

runner: null

evaluation: null

---

# Support Resistance MTF

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Support Resistance MTF derives higher-timeframe price references directly and uses them to draw support/resistance zones on the working chart. The author emphasizes that the higher-timeframe OHLC values are calculated without a security call. Users can choose wick extremes or body prices and adjust local-extreme sensitivity, so the levels represent a configurable view of higher-interval structure rather than a single fixed market definition.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Higher-timeframe extrema detection and level creation/retirement semantics are not sufficiently defined.

- Higher-timeframe extrema detection and level creation/retirement semantics are not sufficiently defined.

## How it works

- Calculate higher-timeframe OHLC from chart data, then identify highest/lowest bars over a selected lookback.
- Use high-low or close-open values to form support/resistance levels or zones.

## Outputs and intended use

- Inspect the resulting higher-timeframe references and adjust transparency/colors for chart readability.

## Parameters and stated settings

- Timeframe selection can be automatic or manual, spanning listed minute intervals through annual intervals; the source illustrates a 15-minute chart with a 4-hour reference.
- Period for Highest/Lowest Bars controls lookback sensitivity, with smaller values more sensitive. No default lookback is disclosed.

## Failure modes and caveats

- Analytical: manually reconstructed intervals depend on chart/session alignment; the absence of security calls alone proves no non-repainting behavior.

## Missing information and implementation boundary

- Auto-timeframe mapping, aggregation boundaries, pivot confirmation rules and level invalidation are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
the script does NOT use Security function
```

### E2: parameters, readiness

```text
smaller numbers = more sensitive result.
```

### E3: parameters, readiness

```text
An example for 15 min chart, 4hours selected as HTF
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_e9l1xaqd_support_resistance_mtf](../tv_e9l1xaqd_support_resistance_mtf.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/E9l1xAQd-Support-Resistance-MTF/

Publication ID: E9l1xAQd. Source SHA-256: 3d56dc8fef55e07f06bcb997df78c1078203c6b110b443851f35ff810b95eab5. Raw-description SHA-256: b91522fd754121dd40ee0aafa8bd15ddb063367cdca8185cfce69749975a5784.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
