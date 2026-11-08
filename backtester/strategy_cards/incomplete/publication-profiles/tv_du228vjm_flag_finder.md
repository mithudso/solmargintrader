---

id: tv_profile_du228vjm

name: "Flag Finder"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Flag Finder detects configurable bullish and bearish continuation formations. It separates an initial directional pole from the subsequent consolidation and offers alerts both when a pattern appears and when price breaks its relevant boundary. The intended application is breakout-oriented trade selection within an existing trend. The educational description associates a strong pole with heavy volume and a quiet flag with drying volume, but does not establish that the coded detector enforces those volume ideas. Its numerical pattern tolerances are customizable, allowing different definitions across timeframes and volatility regimes."

registry_key: null

runner: null

evaluation: null

---

# Flag Finder

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Flag Finder detects configurable bullish and bearish continuation formations. It separates an initial directional pole from the subsequent consolidation and offers alerts both when a pattern appears and when price breaks its relevant boundary. The intended application is breakout-oriented trade selection within an existing trend. The educational description associates a strong pole with heavy volume and a quiet flag with drying volume, but does not establish that the coded detector enforces those volume ideas. Its numerical pattern tolerances are customizable, allowing different definitions across timeframes and volatility regimes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pole/flag anchoring and search/overlap rules are not disclosed.

- Pole/flag anchoring and search/overlap rules are not disclosed.

## How it works

- Search for a directional pole meeting configurable percentage and duration bounds.
- Accept a following flag within depth/rally and bar-count constraints.
- Identify a bull breakout above the flag’s left-side high or bear breakout below its left-side low.

## Outputs and intended use

- Pattern drawings/visibility controls and four alert categories distinguish new bull/bear flags from their breakouts.

## Parameters and stated settings

- Pole minimum/maximum percentage move, flag maximum retracement/rally and each component’s minimum/maximum bars are user inputs.
- Colors and visible components are adjustable; numeric defaults are absent.

## Failure modes and caveats

- Continuation labels do not guarantee continuation, and tuned geometry can overfit.
- Volume narrative should not be assumed to be an implemented filter.

## Missing information and implementation boundary

- Exact anchoring/search order, overlap handling, confirmation timing, volume tests, defaults, stops and targets are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price percentages, extrema, bar counts and any described volume context are OHLCV-compatible.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
minimum and maximum accepted limits from the % gain loss required for the pole
```

### E2: parameters

```text
maximum acceptable flag depth or rally
```

### E3: mechanism, outputs_and_use

```text
above the left side high of a bull flag or below the left side low of a bear flag.
```

### E4: parameters, outputs_and_use

```text
four different types of alerts
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_du228vjm_flag_finder](../tv_du228vjm_flag_finder.md)
- [tv_method_flag_pennant](../tv_method_flag_pennant.md)

## Source

https://www.tradingview.com/script/DU228Vjm-Flag-Finder/

Publication ID: DU228Vjm. Source SHA-256: 44f8693f9318352549e2ab69b57f6466ed151f09f6e932ce7c4c73d827529c62. Raw-description SHA-256: 9620c4b5b02ea5d7cd8c3dfaaed9d7946e93eee24bd36ba2b5c68d5b7b6c6e05.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
