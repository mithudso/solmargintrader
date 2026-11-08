---

id: tv_profile_p0h2afk4

name: "Probability of ATR Index [racer8]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Probability of ATR Index estimates the chance of price reaching a selected ATR distance within a chosen future horizon. The author proposes stop-distance assessment and options-range selection as applications. It combines ATR and price standard deviation in a normal-distribution approximation evaluated through a Taylor-series integral substitute. The description does not establish whether the probability is a terminal-price event or a pathwise barrier hit, a decisive distinction for stops and range options. Its probability should therefore be treated as an unvalidated model output rather than an empirically calibrated likelihood."

registry_key: null

runner: null

evaluation: null

---

# Probability of ATR Index [racer8]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Probability of ATR Index estimates the chance of price reaching a selected ATR distance within a chosen future horizon. The author proposes stop-distance assessment and options-range selection as applications. It combines ATR and price standard deviation in a normal-distribution approximation evaluated through a Taylor-series integral substitute. The description does not establish whether the probability is a terminal-price event or a pathwise barrier hit, a decisive distinction for stops and range options. Its probability should therefore be treated as an unvalidated model output rather than an empirically calibrated likelihood.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The probability equation, horizon scaling and Taylor approximation are undisclosed.

- The probability equation, horizon scaling and Taylor approximation are undisclosed.

## How it works

- Combine current ATR, price standard deviation, ATR-distance input and horizon input in an undisclosed model.
- Approximate normal-distribution integral values with a Taylor expansion and combine halves into the stated probability.

## Outputs and intended use

- Hotter colors indicate higher estimated reach probability; pane values show probability and its average.

## Parameters and stated settings

- ATR distance and future bar count are explicit controls; indicator lengths/defaults are absent.

## Failure modes and caveats

- Terminal normal probabilities do not generally equal first-passage stop-hit probabilities.
- The prose incorrectly pairs a standard-normal density centered at zero with mean one, signaling ambiguity.
- Fat tails, changing volatility and numerical approximation error can invalidate estimates.

## Missing information and implementation boundary

- Exact probability equation, horizon scaling, Taylor order/range, ATR/deviation lengths, averaging and calibration are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. ATR and price dispersion are OHLCV-derived; the barrier-probability model is an algorithm gap.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
ATR distance and # bars (time).
```

### E2: mechanism, readiness

```text
integral calculus & the Taylor series
```

### E3: outputs_and_use

```text
probability & average probability
```

### E4: risks

```text
mu (mean) = 1
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_p0h2afk4_probability_of_atr_index_racer8](../tv_p0h2afk4_probability_of_atr_index_racer8.md)

## Source

https://www.tradingview.com/script/P0H2AFk4-Probability-of-ATR-Index-racer8/

Publication ID: P0H2AFk4. Source SHA-256: b1150aaeabaa132d8013080cb12daa67d8733ca21c50d1eba1cd45081675bc1a. Raw-description SHA-256: 5b9f99b854cda6326ac9c9f74fc559791921e25e76397a0d69c82a51a5670d14.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
