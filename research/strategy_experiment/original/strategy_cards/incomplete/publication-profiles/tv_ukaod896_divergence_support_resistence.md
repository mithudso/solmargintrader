---

id: tv_profile_ukaod896

name: "Divergence-Support/Resistence"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Divergence-Support/Resistance filters a zigzag’s many pivots to retain only those associated with regular or hidden oscillator divergence. The author treats divergence as temporary momentum weakness that can define a reference area rather than a standalone reversal command. Line color records the divergence type, while the line’s location relative to current price determines whether it acts as support or resistance."

registry_key: null

runner: null

evaluation: null

---

# Divergence-Support/Resistence

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Divergence-Support/Resistance filters a zigzag’s many pivots to retain only those associated with regular or hidden oscillator divergence. The author treats divergence as temporary momentum weakness that can define a reference area rather than a standalone reversal command. Line color records the divergence type, while the line’s location relative to current price determines whether it acts as support or resistance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Zigzag finalization, oscillator-period mapping and divergence tests are unspecified.

- Zigzag finalization, oscillator-period mapping and divergence tests are unspecified.

## How it works

- Build zigzag pivots, derive oscillator periods from zigzag length and detect regular/hidden divergence.
- Draw horizontal levels only at divergence-associated pivots; omit continuation and indecision pivots and annotate divergence symbols.

## Outputs and intended use

- Read green/red shades as bullish/bearish divergence provenance, not permanent support/resistance identity. Any level below price is support and above price resistance in the proposed interpretation.

## Parameters and stated settings

- Inputs are zigzag lengths and oscillator choice, optionally an external oscillator source; periods are automatically calculated but their mapping and defaults are undisclosed.

## Failure modes and caveats

- Analytical: zigzag pivots may require later confirmation and divergence can persist against the dominant trend; level origin timing matters.

## Missing information and implementation boundary

- Pivot finalization, divergence equations, oscillator-period mapping, level expiration and executable risk rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
draw support resistence lines only on pivots which has observed either divergence or hidden divergence.
```

### E2: parameters, readiness

```text
Oscillator periods are automatically calculated based on zigzag length.
```

### E3: outputs_and_use, readiness

```text
Any lines which are below the price should be treated as support
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_ukaod896_divergence_support_resistence](../tv_ukaod896_divergence_support_resistence.md)

## Source

https://www.tradingview.com/script/UkaoD896-Divergence-Support-Resistence/

Publication ID: UkaoD896. Source SHA-256: 271ea2be8852d2802de6f57fc40d6cf64374e870e85afe0769d4c7988869f996. Raw-description SHA-256: a7ba83bae3b74cb55f3fd01af8b82e343faadff615b06c88b13d26b7f2b59099.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
