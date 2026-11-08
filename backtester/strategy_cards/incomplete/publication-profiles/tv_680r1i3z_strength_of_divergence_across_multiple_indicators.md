---

id: tv_profile_680r1i3z

name: "Strength of Divergence Across Multiple Indicators"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Rank price/indicator divergences by a weighted magnitude score and summarize agreement across multiple technical indicators."

registry_key: null

runner: null

evaluation: null

---

# Strength of Divergence Across Multiple Indicators

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Rank price/indicator divergences by a weighted magnitude score and summarize agreement across multiple technical indicators.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Correct normalization parentheses, total component combination, zero-variance treatment, pivot confirmation and execution rules require code clarification.

- Correct normalization parentheses, total component combination, zero-variance treatment, pivot confirmation and execution rules require code clarification.

## How it works

- For each divergent indicator combine pivot-to-pivot absolute price change with indicator change, intended to be scaled by standard deviation. Weight divergence type, components and indicators, then sum the individual strengths on each bar.

## Outputs and intended use

- Labels show aggregate strength and number of divergent indicators; tooltips break down individual contributions. Use this as comparative divergence context rather than treating the total as a calibrated reversal probability.

## Parameters and stated settings

- Regular/hidden weights default one each; price/indicator component weights 0.5/1.5; RSI 1.1, OBV 0.8, MACD 0.9 and stochastic 0.9. Pivot lengths, search limits, sources and display are configurable.

## Failure modes and caveats

- The printed normalization expression is ambiguous: division by two followed by multiplication by standard deviation differs from dividing by twice standard deviation. Correlated indicators also inflate apparent agreement.

## Missing information and implementation boundary

- Correct normalization parentheses, total component combination, zero-variance treatment, pivot confirmation and execution rules require code clarification.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supplies the described input class; this does not verify code parity, complete historical data or measured returns.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
|indicator_value_1 - indicator_value_2| / 2 * StDev(indicator_series,100)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Regular divergence weight - default = 1
Hidden divergence weight - default = 1
ΔPrice weight - default = 0.5
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
ΔIndicator weight - default = 1.5
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
RSI weight - default = 1.1
OBV weight - default = 0.8
MACD weight - default = 0.9
STOCH weight - default = 0.9
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_680r1i3z_strength_of_divergence_across_multiple_indicators](../tv_680r1i3z_strength_of_divergence_across_multiple_indicators.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_method_rsi_divergence](../../../strategy_research/tv_method_rsi_divergence.md)

## Source

https://www.tradingview.com/script/680R1I3Z-Strength-of-Divergence-Across-Multiple-Indicators/

Publication ID: 680R1I3Z. Source SHA-256: ecfef2440fc0c22ba51e194d5deee3213306012ad0cffefe36e4b2b87659a99c. Raw-description SHA-256: 66562e9cb437fd1e1aec9dff0b5c213f476185718c4c5352e9ec38494d67f572.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
