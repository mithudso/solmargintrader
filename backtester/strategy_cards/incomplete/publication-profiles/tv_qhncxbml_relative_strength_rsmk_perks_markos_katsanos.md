---

id: tv_profile_qhncxbml

name: "Relative Strength(RSMK) + Perks - Markos Katsanos"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare an asset's performance with a chosen market benchmark using RSMK and an optional companion comparative-strength formulation."

registry_key: null

runner: null

evaluation: null

---

# Relative Strength(RSMK) + Perks - Markos Katsanos

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare an asset's performance with a chosen market benchmark using RSMK and an optional companion comparative-strength formulation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: RSMK formula, companion equation, price adjustments, timeframe synchronization and crossover/trading rules are missing.

- RSMK formula, companion equation, price adjustments, timeframe synchronization and crossover/trading rules are missing.

## How it works

- Implement Katsanos' relative-strength idea and the author's separate similar algorithm. A custom EMA replacement accepts fractional periods, but the saved prose does not disclose either complete relative-strength equation.

## Outputs and intended use

- Use the two curves to inspect relative outperformance/underperformance. The author explicitly distinguishes the tool from RSI; it compares assets rather than measuring one asset's bounded momentum.

## Parameters and stated settings

- Benchmark options include S&P 500, Dow Jones and Nasdaq. The companion algorithm and dark background can be disabled. Numerical lookbacks and default benchmark are not listed.

## Failure modes and caveats

- Benchmark selection affects apparent strength, and similar companion algorithms are not independent evidence. Fractional-period smoothing requires validation of its actual recursion.

## Missing information and implementation boundary

- RSMK formula, companion equation, price adjustments, timeframe synchronization and crossover/trading rules are missing.

## Data requirements

Required inputs: chart asset and selected benchmark price histories.

Repository input-class support: unavailable or unresolved. The selected benchmark and aligned history are external to one chart and are not supplied here.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This indicator is used to compare performance of an asset to a market index of your choosing.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
I included the S&P 500 index along side the Dow Jones and the NASDAQ indices selectively
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
My ema() will also accept a floating point number for the period
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qhncxbml_relative_strength_rsmk_perks_markos_katsanos](../tv_qhncxbml_relative_strength_rsmk_perks_markos_katsanos.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/qhNCXBmL-Relative-Strength-RSMK-Perks-Markos-Katsanos/

Publication ID: qhNCXBmL. Source SHA-256: f6db8a842248b1622f48cf1dc0c570acc82110ecca70f2fc64f70e698cb2f65e. Raw-description SHA-256: 3f77969cac0bf1e10a1213d1d2de5190df06a4f21b64a2acdf38ffd66e5e15be.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
