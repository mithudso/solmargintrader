---

id: tv_profile_jxgpf0jz

name: "TASC 2024.07 Gaps and Extreme Closes"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Gaps and Extreme Closes summarizes historical stock behavior after selected large directional price events. It aims to help research expectations during volatile conditions such as earnings periods by quantifying how often moves occur and how they retrace or close. Users choose opening gaps versus extreme closes and direction, then inspect results by magnitude bucket. The description does not define the event bases, pullback horizon or close normalization, so it cannot substantiate a specific gap-fade or continuation strategy. Reported statistics are descriptive outputs rather than a complete trading backtest."

registry_key: null

runner: null

evaluation: null

---

# TASC 2024.07 Gaps and Extreme Closes

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Gaps and Extreme Closes summarizes historical stock behavior after selected large directional price events. It aims to help research expectations during volatile conditions such as earnings periods by quantifying how often moves occur and how they retrace or close. Users choose opening gaps versus extreme closes and direction, then inspect results by magnitude bucket. The description does not define the event bases, pullback horizon or close normalization, so it cannot substantiate a specific gap-fade or continuation strategy. Reported statistics are descriptive outputs rather than a complete trading backtest.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core event/bucket and pullback/closing outcome definitions are undisclosed.

## How it works

- Classify directional opening-gap or extreme-close events into predefined percentage ranges.
- Count occurrences and average subsequent pullbacks/closing behavior within each bucket.

## Outputs and intended use

- A separate-pane table provides event frequency, average retracement and average-close context.

## Parameters and stated settings

- Event type and upward/downward direction are configurable; magnitude ranges are predefined but not listed.

## Failure modes and caveats

- Conditional averages hide tail risks and may use small/regime-specific samples.
- Unspecified observation horizon prevents translating pullback statistics into orders.

## Missing information and implementation boundary

- Gap/close return bases, bucket edges, horizon, pullback formula, missing events and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price gaps/extremes and subsequent ranges derive from OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
"Opening Gaps" or "Extreme Closes"
```

### E2: parameters

```text
"Upward" or "Downward"
```

### E3: mechanism, readiness

```text
within predefined percentage ranges.
```

### E4: outputs_and_use

```text
average retracement (pullback)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jxgpf0jz_tasc_2024_07_gaps_and_extreme_closes](../tv_jxgpf0jz_tasc_2024_07_gaps_and_extreme_closes.md)

## Source

https://www.tradingview.com/script/jxgPf0jZ-TASC-2024-07-Gaps-and-Extreme-Closes/

Publication ID: jxgPf0jZ. Source SHA-256: 5923008f61de8aa879096a815ea9b0eb8790c2f584b6293a353bd2d6a86641df. Raw-description SHA-256: 5753ecc1e65fe2942a9a955aceef72e1d8c35724ddd51cbcbe65a68cc9225c5c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
