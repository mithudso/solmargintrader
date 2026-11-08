---

id: tv_profile_atzwb4pu

name: "BIN Based Support and Resistance [SS]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Estimate recurring price regions by grouping an entire lookback range into bins instead of relying only on isolated swing extrema."

registry_key: null

runner: null

evaluation: null

---

# BIN Based Support and Resistance [SS]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate recurring price regions by grouping an entire lookback range into bins instead of relying only on isolated swing extrema.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The bin concept and confirmation count are given, but price sampling and the rule selecting support/resistance from the bins remain undefined.

- Price sampling and bin boundaries
- Per-bin aggregation and level selection
- Historical evaluation timing

## How it works

- Partition price action into ten bins and average values within bins to derive central-tendency support/resistance references. Evaluate historical line behavior using three consecutive closes above support or below resistance.

## Outputs and intended use

- Display evaluation counts on lines or in a table, or hide them. Nearby lines are interpreted as consolidation/pseudo-POC context; no volume weighting is established by that analogy.

## Parameters and stated settings

- Lookback is adjustable; suggested values are 250-500 candles intraday and 252 daily. The bin count is described as ten.

## Failure modes and caveats

- The author warns about overshoot, volatile-range distortion and levels beyond the limited sample. Central tendency is not a guaranteed rejection price, and retrospective lines can shift as the sample rolls.

## Missing information and implementation boundary

- Bin membership across OHLC data, exact averaging, choice of plotted bins, backtest sampling and boundary rules are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; source-code parity and cached historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
groups the price action into 10 separate bins.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
averaging the values in the Bins
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
3 consecutive closes above the support line or below the resistance line.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
between 250 to 500 candles on smaller timeframes. I also suggest 252 on daily timeframes
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_atzwb4pu_bin_based_support_and_resistance_ss](../tv_atzwb4pu_bin_based_support_and_resistance_ss.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/AtzwB4pU-BIN-Based-Support-and-Resistance-SS/

Publication ID: AtzwB4pU. Source SHA-256: 5f3f99c6fd6c54511b2fb3f6119e2b534ff73f7f44c4d7d90e3cad7a7e0c3a89. Raw-description SHA-256: 6da5331dd3faa8723d4052a8ef4ad8fdb10ff5b8f6b78ae52c0564e522a79198.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
