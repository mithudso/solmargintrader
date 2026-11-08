---

id: tv_profile_fhtldun5

name: "Portfolio Backtester Engine"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Portfolio Backtester Engine runs one strategy across several securities and aggregates separately funded results. It aims to broaden robustness research beyond one chart’s history and regime. Initial capital is split equally, so it is not an unconstrained pooled-capital allocator. The source adapts a study-based engine but explicitly removes external-indicator coupling and alerts. Combining assets does not automatically provide independent trades or prove robustness; sample-size guidance remains heuristic."

registry_key: null

runner: null

evaluation: null

---

# Portfolio Backtester Engine

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Portfolio Backtester Engine runs one strategy across several securities and aggregates separately funded results. It aims to broaden robustness research beyond one chart’s history and regime. Initial capital is split equally, so it is not an unconstrained pooled-capital allocator. The source adapts a study-based engine but explicitly removes external-indicator coupling and alerts. Combining assets does not automatically provide independent trades or prove robustness; sample-size guidance remains heuristic.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core strategy/fill/risk engine rules and defaults are not supplied.

## How it works

- Run built-in or code-added signed signals per security with selected filters, entry stops, pyramiding and hard exits.
- Split capital equally and aggregate performance bar by bar.

## Outputs and intended use

- Portfolio profit, trade-duration, drawdown/loss-run, ratios, exposure and ROI tables support research.

## Parameters and stated settings

- Up to five securities; signals +1/-1/0; filters/pyramiding default off.
- Built-ins include RSI,MACD,MA cross,Supertrend; circuit breakers/reversals optional.

## Failure modes and caveats

- Correlated trades inflate effective sample counts.
- Drawdown alone does not define sufficient capital; historical tables omit disclosed fill assumptions.
- Alerts are explicitly excluded.

## Missing information and implementation boundary

- Strategy predicates/defaults, fills/costs, sizing, circuit breakers and metric formulas are absent.

## Data requirements

Required inputs: multi-security ohlcv, strategy/risk configuration.

Repository input-class support: unavailable or unresolved. Portfolio histories and strategy settings are external/not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
up to 5 securities
```

### E2: parameters, mechanism

```text
(buy 1 / sell -1/ neutral 0)
```

### E3: mechanism

```text
initial capital is equally distributed
```

### E4: parameters

```text
by default these are all off.
```

### E5: parameters

```text
By default this is off.
```

### E6: risks

```text
Alerts (These may be added in the future
```

### E7: readiness

```text
modify the source code and follow the built-in example.
```

## Source

https://www.tradingview.com/script/fhTLDun5-Portfolio-Backtester-Engine/

Publication ID: fhTLDun5. Source SHA-256: b3ebef473758524148646e8f865cc2804f642b9eddb58f92c695887d0ca2f15f. Raw-description SHA-256: 3b4e8cf749ed80a88b55aef3a22c43796188b52ebb8aacdf293347e4077b79ad.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
