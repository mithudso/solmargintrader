---

id: tv_profile_dq9wjj11

name: "Average Volume Profile"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Average Volume Profile divides a volume-style profile by a market-profile-style measure to show average activity at each price area. It adds a highest-average-volume reference and current-volume comparisons, but the author explicitly says they are unsure how useful the result is. This is exploratory market profiling, not a validated signal or an instruction that the highlighted level should hold."

registry_key: null

runner: null

evaluation: null

---

# Average Volume Profile

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Average Volume Profile divides a volume-style profile by a market-profile-style measure to show average activity at each price area. It adds a highest-average-volume reference and current-volume comparisons, but the author explicitly says they are unsure how useful the result is. This is exploratory market profiling, not a validated signal or an instruction that the highlighted level should hold.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Profile allocation, denominator definition, zero handling, value-zone algorithm and normalization are undisclosed.

- Profile allocation, denominator definition, zero handling, value-zone algorithm and normalization are undisclosed.

## How it works

- Estimate average volume per price area from the ratio of volume profile to market profile, then locate highest average volume and related value zones.
- Compare current distributed candle volume with the average at current price using readouts, a floating line and changing labels.

## Outputs and intended use

- Inspect HAV, current-price average and current distributed volume for research and relative-activity context.

## Parameters and stated settings

- No range length, bin size, market-profile counting convention, value-area percentage or defaults are supplied.

## Failure modes and caveats

- The author questions practical usefulness; analytical: a small time/count denominator can exaggerate average volume in rarely visited areas.

## Missing information and implementation boundary

- Profile allocation, denominator definition, zero handling, value-zone algorithm and normalization are undisclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
volume profile divided by a market profile.
```

### E2: risks, readiness

```text
I am not entirely sure of how to make use of the information
```

### E3: outputs_and_use, readiness

```text
highest average volume point (HAV)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dq9wjj11_average_volume_profile](../tv_dq9wjj11_average_volume_profile.md)
- [tv_method_market_profile](../tv_method_market_profile.md)

## Source

https://www.tradingview.com/script/dQ9Wjj11-Average-Volume-Profile/

Publication ID: dQ9Wjj11. Source SHA-256: edc805b13308ecca4f88e0888d1c509e39af34bc8bd11ff19d50f1c352401943. Raw-description SHA-256: 28c78ff33f7c35c21aed598692b9eec1a76f627ef262f999e3c8a908b5a7176c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
