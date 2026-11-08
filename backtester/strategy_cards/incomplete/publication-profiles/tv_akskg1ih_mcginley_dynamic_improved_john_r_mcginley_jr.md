---

id: tv_profile_akskg1ih

name: "McGinley Dynamic (Improved) - John R. McGinley, Jr."

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "McGinley Dynamic Improved modifies an adaptive moving-average formulation to address numerical instability reported by the author. The described failure modes are collapse toward zero and explosive spikes during unusual volatility. The adaptation inserts minimum/maximum constraints into the divisor and provides plots for comparison with a generic EMA and an unconstrained version. Its purpose is a more stable reusable trend-smoothing component, not a standalone trade signal. The source explains the intended safeguard but does not expose the actual bounds or prove stability across all possible inputs."

registry_key: null

runner: null

evaluation: null

---

# McGinley Dynamic (Improved) - John R. McGinley, Jr.

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

McGinley Dynamic Improved modifies an adaptive moving-average formulation to address numerical instability reported by the author. The described failure modes are collapse toward zero and explosive spikes during unusual volatility. The adaptation inserts minimum/maximum constraints into the divisor and provides plots for comparison with a generic EMA and an unconstrained version. Its purpose is a more stable reusable trend-smoothing component, not a standalone trade signal. The source explains the intended safeguard but does not expose the actual bounds or prove stability across all possible inputs.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The clamped adaptive-average recurrence and constraint bounds are absent.

- The clamped adaptive-average recurrence and constraint bounds are absent.

## How it works

- Retain the McGinley-style adaptive calculation while applying min/max constraints to the exponent-sensitive denominator.
- Plot the improved result from the first chart bar and compare it with EMA and an unconstrained function.

## Outputs and intended use

- Improved moving-average plot and reusable imd() support trend-smoothing research.
- The unconstrained umd() is included for demonstration and explicitly discouraged for published use.

## Parameters and stated settings

- Experimental tweaks are offered, but names/defaults and numeric constraint bounds are not specified.
- The author discusses a fourth-power term as the source of sensitivity.

## Failure modes and caveats

- Clamping changes adaptive behavior and can introduce its own discontinuities.
- The author’s numerical explanation is qualitative; denominator constraints do not by themselves establish safe initialization or all-input stability.

## Missing information and implementation boundary

- Exact recurrence, clamp bounds, length/source defaults, initialization and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The moving-average comparison is price-based and compatible with OHLCV; absent equations are implementation gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
two constraints applied to it using min/max() functions.
```

### E2: parameters, risks

```text
exponent to the power of four
```

### E3: outputs_and_use

```text
plots from bar_index==0
```

### E4: risks

```text
strongly advise against the use of umd()
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_akskg1ih_mcginley_dynamic_improved_john_r_mcginley_jr](../tv_akskg1ih_mcginley_dynamic_improved_john_r_mcginley_jr.md)

## Source

https://www.tradingview.com/script/AKsKg1ih-McGinley-Dynamic-Improved-John-R-McGinley-Jr/

Publication ID: AKsKg1ih. Source SHA-256: 3e08b6a58624dd787ae92d16af667f4907c8c784820817704938bb89e3f0f641. Raw-description SHA-256: 584103e4c775871469e93d013b6b98293bf5197cffeef368bab42407cd166307.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
