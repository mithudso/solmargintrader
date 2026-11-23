---

id: tv_profile_ou82izcq

name: "Reversal finder"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Reversal Finder highlights candles that reject a recent price extreme while showing a large range and close/open placement consistent with a rejection. It targets possible reversals after false breaks of support or resistance. The range filter tries to exclude small, less distinctive candles, while the end-of-bar placement filter emphasizes the rejection geometry rather than merely any new high or low."

registry_key: null

runner: null

evaluation: null

---

# Reversal finder

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Reversal Finder highlights candles that reject a recent price extreme while showing a large range and close/open placement consistent with a rejection. It targets possible reversals after false breaks of support or resistance. The range filter tries to exclude small, less distinctive candles, while the end-of-bar placement filter emphasizes the rejection geometry rather than merely any new high or low.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Prior-window extremes, prior-range SMA multiple and open/close end-of-range thresholds define parameterized rejection candles; equality conventions can be explicit boundaries.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Define reference highs/lows from prior bars, compare the signal candle’s range with an SMA of prior ranges, and filter by a configurable range multiple.
- Require both open and close near the appropriate end of the bar to emphasize failed breaks; optionally color candidate bars.

## Outputs and intended use

- Green denotes buy candidates, red sell candidates and gray other bars when highlighting is enabled.

## Parameters and stated settings

- Controls are lookback, range-SMA length, range multiple and range threshold. Example settings, expressly not defaults, are 5, 20, 1.2 and 33%.

## Failure modes and caveats

- Analytical: rejection patterns can fail during trends; live-candle geometry can change before confirmation.

## Missing information and implementation boundary

- Exact inequality/break rules, default values, bar-close confirmation, alerts and stop/target rules are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; source-code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
lookback: 5, SMA length: 20, range multiple: 1.2, range threshold: 33%.
```

### E2: mechanism, readiness

```text
both the open and close of the bar are at the extreme end of the bar
```

### E3: outputs_and_use, readiness

```text
buy signal in green, sell signal bars in red, and all other bars in grey.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_ou82izcq_reversal_finder](../tv_ou82izcq_reversal_finder.md)

## Source

https://www.tradingview.com/script/OU82iZCq-Reversal-finder/

Publication ID: OU82iZCq. Source SHA-256: 3bab69d8873e6b4533080cd0c24aed08a98a8a7d57f26b3b31d48347db95998a. Raw-description SHA-256: a1345da54b5564577c7d072a57c890c206737ade18c426558795a5dde50bfefc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
