---

id: tv_profile_b094banp

name: "Laguerre RSI"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Laguerre RSI uses a Laguerre-filter-based version of RSI to reduce the noise the author associates with conventional RSI. The intended interpretation combines threshold recrossings with a different meaning for sustained extremes: crossing back from an extreme is offered as a trade cue, while remaining pinned at an extreme is described as evidence of trend strength. That distinction matters because an extreme reading alone is not described as an automatic reversal."

registry_key: null

runner: null

evaluation: null

---

# Laguerre RSI

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Laguerre RSI uses a Laguerre-filter-based version of RSI to reduce the noise the author associates with conventional RSI. The intended interpretation combines threshold recrossings with a different meaning for sustained extremes: crossing back from an extreme is offered as a trade cue, while remaining pinned at an extreme is described as evidence of trend strength. That distinction matters because an extreme reading alone is not described as an automatic reversal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Laguerre filter recursion and RSI calculation are absent; threshold cues alone do not define the indicator.

- Laguerre filter recursion and RSI calculation are absent; threshold cues alone do not define the indicator.

## How it works

- Apply John Ehlers’ Laguerre-filter approach to RSI; alpha adjusts the balance between lag and smoothness.
- Interpret upward recrossing of the lower threshold as a buy cue and downward recrossing of the upper threshold as a sell cue.

## Outputs and intended use

- Buy on a cross upward above 20 and sell on a cross downward below 80, according to the source.
- A flat reading above 80 is interpreted as a strong uptrend; a flat reading below 20 as a strong downtrend.

## Parameters and stated settings

- Alpha is configurable but its default and permitted range are not stated; the disclosed interpretation uses levels 20 and 80.

## Failure modes and caveats

- Analytical: recrossings can whipsaw and persistent extremes can postpone reversal signals; no sizing or stop rules accompany the cues.

## Missing information and implementation boundary

- Filter recursion, RSI normalization, crossing confirmation and whether sell means close-long or initiate-short are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart price/volume data supports the described calculation class; matching Pine implementation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
Change alpha coefficient to increase/decrease lag and smoothness.
```

### E2: parameters, outputs_and_use, readiness

```text
Buy when Laguerre RSI crosses upwards above 20.
Sell when Laguerre RSI crosses down below 80.
```

### E3: outputs_and_use, readiness

```text
While indicator runs flat above 80 level, it means that an uptrend is strong.
While indicator runs flat below 20 level, it means that a downtrend is strong.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_b094banp_laguerre_rsi](../tv_b094banp_laguerre_rsi.md)

## Source

https://www.tradingview.com/script/B094baNp-Laguerre-RSI/

Publication ID: B094baNp. Source SHA-256: c5aa8ed03bbbf4790f9bc49b03ad9e26dbf9d857f582e6b80ca8e6cc14411d68. Raw-description SHA-256: da2a3cb16c21c32448a5d7f0044b3eb684f4889c642a27067ad5cfcdccf2b0bf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
