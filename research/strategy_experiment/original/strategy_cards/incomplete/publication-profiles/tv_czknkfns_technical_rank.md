---

id: tv_profile_czknkfns

name: "Technical Rank"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Technical Rank combines long-, medium- and short-term technical features, then compares the resulting scores across a selected group of securities. It aims to identify relative strength for pullback research and avoid weaker peers. The component mix is described explicitly, but the transformation from raw weighted score into peer rank is not explained, so the stated scale should not be reverse-engineered from the title."

registry_key: null

runner: null

evaluation: null

---

# Technical Rank

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Technical Rank combines long-, medium- and short-term technical features, then compares the resulting scores across a selected group of securities. It aims to identify relative strength for pullback research and avoid weaker peers. The component mix is described explicitly, but the transformation from raw weighted score into peer rank is not explained, so the stated scale should not be reverse-engineered from the title.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** PPO/RSI settings, raw-feature transformations, rank normalization, tie handling and missing-symbol rules are unspecified.

- PPO/RSI settings, raw-feature transformations, rank normalization, tie handling and missing-symbol rules are unspecified.

## How it works

- Combine percentage distance from long/medium EMAs, long/medium ROC, short PPO-histogram slope and RSI with specified weights.
- Calculate for a selected peer set and sort by rank to show improving or deteriorating relative technical performance.

## Outputs and intended use

- Inspect stronger names for potential long pullbacks and weaker names to avoid, with the author recommending multiple-timeframe review.

## Parameters and stated settings

- EMA 200 and ROC 125 each carry 30%; EMA 50 and ROC 20 each 15%; three-day PPO-histogram slope divided by three and RSI each 5%.
- The tool compares ten securities on a stated 0–100 rank scale; source advises matching session types across the basket.

## Failure modes and caveats

- Analytical: basket selection changes relative ranking, correlated components double-count trend and session mismatches compromise comparison.

## Missing information and implementation boundary

- PPO/RSI settings, raw-feature transformations, rank normalization, tie handling and missing-symbol rules are unspecified.

## Data requirements

Required inputs: synchronized OHLCV for ten caller-selected peers.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
200-day exponential moving average (EMA) (30% weight) and the 125-day rate-of-change (ROC) (30% weight).
```

### E2: parameters, readiness

```text
50-day EMA (15%) and the 20-day rate-of-change (15%).
```

### E3: parameters, readiness

```text
Three-day slope of percentage price oscillator histogram divided by three (5%) and the relative strength index (5%).
```

### E4: parameters, readiness

```text
10 different securities
```

### E5: parameters, readiness

```text
A rank of 100
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_czknkfns_technical_rank](../tv_czknkfns_technical_rank.md)

## Source

https://www.tradingview.com/script/czknkFNs-Technical-Rank/

Publication ID: czknkFNs. Source SHA-256: a8eafa77be2552e0f95c045b3547e30452da1fae9140e3db3ec4e85912e3e11c. Raw-description SHA-256: 4781d913a943655fa5230bb0c366d0142b85a1e10bb59a791ddad4f1da67e2c0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
