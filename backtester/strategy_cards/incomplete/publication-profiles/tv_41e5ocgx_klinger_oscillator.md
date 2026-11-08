---

id: tv_profile_41e5ocgx

name: "+ Klinger Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This Klinger variant retains the author-described volume-momentum core while expanding how the oscillator is smoothed and displayed. The purpose is to read volume-associated directional pressure through an oscillator, its signal line and zero reference. Added divergence plots, candle coloring and optional bands give several visual perspectives on that same measure rather than a separately specified strategy."

registry_key: null

runner: null

evaluation: null

---

# + Klinger Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This Klinger variant retains the author-described volume-momentum core while expanding how the oscillator is smoothed and displayed. The purpose is to read volume-associated directional pressure through an oscillator, its signal line and zero reference. Added divergence plots, candle coloring and optional bands give several visual perspectives on that same measure rather than a separately specified strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The underlying volume-force calculation is absent despite disclosed EMA lengths.

- The underlying volume-force calculation is absent despite disclosed EMA lengths.

## How it works

- Compare current high/low/close with the previous period to assign volume direction; subtract two exponential averages of the resulting volume calculation.
- Smooth the oscillator into a selectable signal line and optionally detect divergences on either the oscillator or that signal line.

## Outputs and intended use

- Interpret the oscillator against its signal and zero lines; inspect optional Donchian bands, bar colors, alerts and divergence markers.

## Parameters and stated settings

- Traditional oscillator EMA lengths are 34 and 55; the signal defaults to a 13-period EMA, with alternatives including ALMA, HMA and modular filter.
- Divergence pivot lookbacks and search ranges are adjustable; source says their initial settings follow TradingView RSI defaults without listing the numbers.

## Failure modes and caveats

- Analytical: divergence confirmation can lag and alternative smoothing choices alter timing; combinations are not validated trade rules.

## Missing information and implementation boundary

- Exact volume-force formula, numerical divergence defaults, alert conditions and entry/exit rules are not fully disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart price/volume data supports the described calculation class; matching Pine implementation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
traditionally 34 and 55
```

### E2: parameters, readiness

```text
Usually it's a 13 period EMA, and that comes default
```

### E3: mechanism, readiness

```text
It then takes an EMA of two different lookback periods of that calculation and subtracts one from the other.
```

### E4: mechanism, outputs_and_use, readiness

```text
you can set it to plot divergences off either the Klinger or the signal line.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_builtin_klinger_oscillator](../tv_builtin_klinger_oscillator.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)

## Source

https://www.tradingview.com/script/41E5Ocgx-Klinger-Oscillator/

Publication ID: 41E5Ocgx. Source SHA-256: 50e72d80ef670184e599a8382be341b507adebdc7536eb91f09def7aeb6f8c30. Raw-description SHA-256: 3294a60bace786ef1e3382f93e5904970c8f45ab78515c396ce080fecb39bdcd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
