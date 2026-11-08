---

id: tv_profile_ejmwjmdf

name: "Dynamic Gap Probability Tool"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Dynamic Gap Probability Tool estimates the historical next-candle color associated with the current percentage distance from a selected moving average. It tries to avoid presenting a tiny exact-match sample as reliable by broadening the deviation sample when occurrences are scarce. The table is an empirical conditional-frequency summary, not a calibrated forecast or a rule that resolves whether the trader should favor reversal or continuation."

registry_key: null

runner: null

evaluation: null

---

# Dynamic Gap Probability Tool

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dynamic Gap Probability Tool estimates the historical next-candle color associated with the current percentage distance from a selected moving average. It tries to avoid presenting a tiny exact-match sample as reliable by broadening the deviation sample when occurrences are scarce. The table is an empirical conditional-frequency summary, not a calibrated forecast or a rule that resolves whether the trader should favor reversal or continuation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Exact-bucket versus cumulative tail counting and deduplication are ambiguous in the principal probability estimator.

- Exact-bucket versus cumulative tail counting and deduplication are ambiguous in the principal probability estimator.

## How it works

- Compute percentage gap as close minus moving average divided by the average, then round its absolute size to the nearest percent.
- Count historical deviations on the corresponding side, expand toward more extreme gap buckets when needed, and estimate the next candle’s green/red proportions.

## Outputs and intended use

- Read current gap, sample size and next-candle green/red percentages together; assess reliability before using the result in another strategy.

## Parameters and stated settings

- MA choices include SMA, EMA, WMA, VWMA, HMA, SMMA and TMA. MA period defaults to 200 and minimum occurrences to 50.
- The example broadens an 8% below-average sample toward 9% and 10% gaps; table position/style are adjustable.

## Failure modes and caveats

- Historical probabilities do not guarantee future outcomes; analytical: overlapping threshold counts and retrospective sample expansion may affect independence and interpretation.

## Missing information and implementation boundary

- The prose alternates exact buckets and cumulative inequality counts without explaining deduplication; historical window, doji treatment and causal updating need clarification.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Moving Average Period (default 200)
```

### E2: parameters, readiness

```text
Minimum Occurrences Threshold (default 50)
```

### E3: mechanism, readiness

```text
include gaps at X+1%, X+2%, etc., until threshold is reached.
```

### E4: parameters, readiness

```text
If price is 8% below the SMA but only 20 exact matches exist, the script will include 9% and 10% gaps
```

### E5: risks, readiness

```text
Historical probabilities do not guarantee future performance.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ejmwjmdf_dynamic_gap_probability_tool](../../tv_ejmwjmdf_dynamic_gap_probability_tool.md)

## Source

https://www.tradingview.com/script/EJMwjmDF-Dynamic-Gap-Probability-Tool/

Publication ID: EJMwjmDF. Source SHA-256: e1d5fb5414d24eeda9c1eeba57b70ccd19f2870e6528f5654b8b310c275de22d. Raw-description SHA-256: c7cde6587d3581e1b1fb8eb4d0c4164d20c3b01842dead00cf6abea028285500.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
