---

id: tv_profile_fqnxjggs

name: "Cycles Analysis"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Cycles Analysis retrospectively divides history into bull/bear periods and projects a size/duration region from completed past cycles. It aims at macro visualization rather than realtime trading. Users define changes by percentage movement or absence of a new extreme for a duration. Optional stagnation marks similar inactivity without changing direction or entering statistics. The unfinished cycle is excluded from historical calculations. The author warns that labels can repaint months of history and replay is unsupported because work occurs on the last candle."

registry_key: null

runner: null

evaluation: null

---

# Cycles Analysis

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Cycles Analysis retrospectively divides history into bull/bear periods and projects a size/duration region from completed past cycles. It aims at macro visualization rather than realtime trading. Users define changes by percentage movement or absence of a new extreme for a duration. Optional stagnation marks similar inactivity without changing direction or entering statistics. The unfinished cycle is excluded from historical calculations. The author warns that labels can repaint months of history and replay is unsupported because work occurs on the last candle.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Cycle transition/anchor and projection/percentile calculations are unspecified.

## How it works

- Detect cycles from percentage or no-new-extreme duration rules and mark stagnation separately.
- Use completed cycle sizes for full-range/percentile boxes with mean/median targets.

## Outputs and intended use

- Cycle/stagnation displays and projection boxes support retrospective regime analysis.

## Parameters and stated settings

- At least three periods for percentiles; the source says its90th-percentile example requires twenty.
- Duration display assumes360-day year and30-day month; thresholds configurable without defaults.

## Failure modes and caveats

- Large revisions invalidate backtesting from final labels.
- Small cycle samples distort percentiles; projections are not calibrated forecasts.

## Missing information and implementation boundary

- Exact transition anchors, joint size/duration projection, percentile conventions and defaults absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price extrema/time and historical statistics use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
at least 3 periods
```

### E2: parameters

```text
90 percentile
```

### E3: parameters

```text
(20 in this specific case)
```

### E4: parameters

```text
year = 360 days, and a month = 30 days
```

### E5: risks

```text
repaint the last 6 months
```

### E6: risks, readiness

```text
calculations only once on the last candle.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fqnxjggs_cycles_analysis](../tv_fqnxjggs_cycles_analysis.md)

## Source

https://www.tradingview.com/script/fqnXJggs-Cycles-Analysis/

Publication ID: fqnXJggs. Source SHA-256: 41311d757ef519250b1002da1f9d9cf1b5eba57f9062dac520cca25cc3f32b69. Raw-description SHA-256: 24a01a4578ec0e28475f4c9d0888c5ee993613575e24b88351c170d60e5d9ad7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
