---

id: tv_profile_a7a6ys0y

name: "Chart Patterns Screener [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Chart Patterns Screener adapts an automatic classical-pattern detector to watchlist scanning. It exposes counts of currently relevant patterns so the screener can return symbols with any pattern or a particular family. Its distinctive contribution here is recency filtering and screener integration; the actual geometry is inherited from a separately referenced indicator and is not reconstructed in this description."

registry_key: null

runner: null

evaluation: null

---

# Chart Patterns Screener [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Chart Patterns Screener adapts an automatic classical-pattern detector to watchlist scanning. It exposes counts of currently relevant patterns so the screener can return symbols with any pattern or a particular family. Its distinctive contribution here is recency filtering and screener integration; the actual geometry is inherited from a separately referenced indicator and is not reconstructed in this description.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Inherited pattern equations, pivot rules and geometry thresholds are undisclosed.

- Inherited pattern equations, pivot rules and geometry thresholds are undisclosed.

## How it works

- Detect inherited chart patterns and expose total/type-specific active counts.
- Limit pattern age with a fixed bar window or a window proportional to pattern duration, then scan the user’s watchlist for positive counts.

## Outputs and intended use

- Filter Current Patterns or a named pattern count above zero. On-chart use is intentionally limited and initially displays a note.

## Parameters and stated settings

- Fixed example uses 20 bars; relative example uses 20% so a 100-bar pattern remains active for 20 bars and a 150-bar pattern for 30.
- The historical page mentions a 1,000-symbol watchlist limit; that is not verified current platform policy.

## Failure modes and caveats

- Analytical: pattern counts depend on pivot confirmation and geometry tolerances; age filtering does not establish a remaining trade opportunity.

## Missing information and implementation boundary

- Inherited pattern equations, pivot rules, geometry thresholds, symbol-universe selection and exact defaults are not provided.

## Data requirements

Required inputs: OHLCV for caller-selected watchlist.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: outputs_and_use, readiness

```text
Current Patterns > 0
```

### E2: parameters, readiness

```text
If Fixed bars are 20
```

### E3: parameters, readiness

```text
100 bars
```

### E4: parameters, readiness

```text
20% is set as relative percent
```

### E5: parameters, readiness

```text
150 bars will be flagged if it has formed within 30 bars.
```

### E6: parameters, readiness

```text
maxium 1000 symbols.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_a7a6ys0y_chart_patterns_screener_trendoscope](../tv_a7a6ys0y_chart_patterns_screener_trendoscope.md)
- [tv_method_triangle](../tv_method_triangle.md)
- [tv_method_wedge](../tv_method_wedge.md)

## Source

https://www.tradingview.com/script/a7a6yS0y-Chart-Patterns-Screener-Trendoscope/

Publication ID: a7a6yS0y. Source SHA-256: 6e1fc4a93d09fdaaef2c07dc6e75183acd19b95db734014ad83cd9f4c401614f. Raw-description SHA-256: f274ae18c5d345a44d229710a91071d766e17b0a2c2d49dc301f2b17585b680e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
