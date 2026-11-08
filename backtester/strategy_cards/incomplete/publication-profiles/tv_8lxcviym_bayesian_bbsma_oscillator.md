---

id: tv_profile_8lxcviym

name: "Bayesian BBSMA Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Bayesian BBSMA Oscillator turns relationships to Bollinger bands and a moving average into competing upward/downward probability displays. The author draws inspiration from Bayesian classification and proposes scalping-oriented interpretations, but the document mixes continuation and correction assumptions and prints probability expressions without unambiguous denominator grouping. Its probabilities should therefore be understood as the author’s model outputs rather than calibrated likelihoods."

registry_key: null

runner: null

evaluation: null

---

# Bayesian BBSMA Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Bayesian BBSMA Oscillator turns relationships to Bollinger bands and a moving average into competing upward/downward probability displays. The author draws inspiration from Bayesian classification and proposes scalping-oriented interpretations, but the document mixes continuation and correction assumptions and prints probability expressions without unambiguous denominator grouping. Its probabilities should therefore be understood as the author’s model outputs rather than calibrated likelihoods.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Conditional probability estimation and denominator grouping are ambiguous.

- Conditional probability estimation and denominator grouping are ambiguous.

## How it works

- Use assumptions about price relative to the Bollinger basis, upper band and a shorter moving average to form evidence for two directional events.
- Apply the printed Bayes-style expressions to produce green upward and red downward probability components; the precise event-count estimation is not disclosed.

## Outputs and intended use

- Wait while a component remains pinned at its ceiling or floor. A decrease after a ceiling is called a strong cue and an increase after a floor a weak cue, but the text leaves trade-direction mapping ambiguous.

## Parameters and stated settings

- The author aims to optimize for a 1-hour timeframe and recommends Once per Bar alerts; no MA/Bollinger period defaults or probability thresholds are given.

## Failure modes and caveats

- The author admits unknown timing and movement size. Analytical: ambiguous formulas, dependence between related inputs and contradictory directional assumptions prevent treating outputs as validated probabilities.

## Missing information and implementation boundary

- Training window, priors, conditional frequencies, denominator parentheses, ceiling/floor tolerance and exact long/short mapping are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; code parity is unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Optimize parameters for 1 hour timeframe
```

### E2: parameters, readiness

```text
Use [i]Once per Bar[/i] option when generating alerts.
```

### E3: risks, readiness

```text
We won't know for sure when prices are going to break
```

### E4: mechanism, missing_information, readiness

```text
Pr(Up|Indicator) = Pr(Indicator|Up) * Pr(Up) / Pr(Indicator|Up) * Pr(Up) + Pr(Indicator|Down) * Pr(Down)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8lxcviym_bayesian_bbsma_oscillator](../tv_8lxcviym_bayesian_bbsma_oscillator.md)

## Source

https://www.tradingview.com/script/8lXcviYm-Bayesian-BBSMA-Oscillator/

Publication ID: 8lXcviYm. Source SHA-256: e86ae66f08786bb45030e8151b39b7dcb77af40a0c74c2ceea6c382bc3ffa7a5. Raw-description SHA-256: 2dfafa0aa352bdc83787dd535b041bddf47cb8981a1d0c2a7fdc5e20b91a7aa5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
