---

id: tv_profile_bugfwu53

name: "ATR Based Trendlines - JD"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Draw pivot-anchored trendlines whose slopes reflect volatility at the moment the pivot is detected."

registry_key: null

runner: null

evaluation: null

---

# ATR Based Trendlines - JD

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Draw pivot-anchored trendlines whose slopes reflect volatility at the moment the pivot is detected.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The pivot confirmation rule, ATR formula, direction sign, line lifetime and alert behavior are absent.

- The pivot confirmation rule, ATR formula, direction sign, line lifetime and alert behavior are absent.

## How it works

- Use a percentage of ATR to set each line's angle. The line follows the price-change rate implied by the ATR observed at pivot detection, rather than connecting an arbitrary pair of endpoints.

## Outputs and intended use

- Treat the lines as volatility-scaled reference geometry. A line breach is not given an entry/exit interpretation in the source.

## Parameters and stated settings

- The ATR percentage can be a fraction below 100 or multiple above 100. Pivot length and ATR length/default percentage are not disclosed.

## Failure modes and caveats

- Pivot detection can occur after the turning point. Displayed line angles also depend on chart scaling and should not be treated as universal geometric slopes.

## Missing information and implementation boundary

- The pivot confirmation rule, ATR formula, direction sign, line lifetime and alert behavior are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The angle follows the change in price, dictated by the atr at the moment where the pivot point is detected.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The atr percentage determines if the trendline follows the rate of change of the atr or a fraction ( value < 100) or a multiple ( value > 100) of that
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bugfwu53_atr_based_trendlines_jd](../tv_bugfwu53_atr_based_trendlines_jd.md)
- [tv_method_atr_trailing](../../tv_method_atr_trailing.md)

## Source

https://www.tradingview.com/script/bugFWu53-ATR-Based-Trendlines-JD/

Publication ID: bugFWu53. Source SHA-256: 84602bcf0a539e96295bb1e1e016d18d7523c040e84dc220190fbc7a980f2bbe. Raw-description SHA-256: 22f19a21a19f1b92700e51ccd7df5cf27c6a0dad70e79d9d88d5b3823bf9d8ab.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
