---

id: tv_profile_ej53t8wv

name: "Support Resistance Channels"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Support Resistance Channels groups nearby pivots into zones, ranks their strength and displays the strongest candidates. A newly detected pivot triggers reconstruction of the channel set, so the zones respond to evolving structure rather than remain fixed manual drawings. Break markers and alerts help the trader notice when the latest movement leaves one of those zones, while display controls manage clutter."

registry_key: null

runner: null

evaluation: null

---

# Support Resistance Channels

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Support Resistance Channels groups nearby pivots into zones, ranks their strength and displays the strongest candidates. A newly detected pivot triggers reconstruction of the channel set, so the zones respond to evolving structure rather than remain fixed manual drawings. Break markers and alerts help the trader notice when the latest movement leaves one of those zones, while display controls manage clutter.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Channel strength calculation and overlap/selection rules are undisclosed.

- Channel strength calculation and overlap/selection rules are undisclosed.

## How it works

- Store pivot points, search neighboring pivots inside a dynamically sized channel, calculate channel strength and sort the candidates.
- Rebuild channels when a new pivot arrives, retain the strongest for display and update colors; detect broken channels on the last move.

## Outputs and intended use

- Inspect the ranked zones and use optional above/below-candle shapes and alerts for breaks.

## Parameters and stated settings

- Controls include Pivot Period, wick versus body source, maximum channel width, count displayed, pivot lookback, visible-bar limit and Start Date.
- Maximum channel width uses highest/lowest levels over the last 300 bars; a display example shows the last 100 bars.

## Failure modes and caveats

- Analytical: rebuilding can change old-looking levels and pivot confirmation timing matters; the author notes old zones can distort chart visibility.

## Missing information and implementation boundary

- Strength formula, pivot confirmation, overlap resolution, breakout condition and defaults are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Highest/Lowest levels in last 300 bars
```

### E2: parameters, readiness

```text
set 100:
```

### E3: mechanism, readiness

```text
when it found a new Pivot Point it clears older S/R channels
```

### E4: mechanism, readiness

```text
then sorts all S/R channels by strength
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ej53t8wv_support_resistance_channels](../tv_ej53t8wv_support_resistance_channels.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/Ej53t8Wv-Support-Resistance-Channels/

Publication ID: Ej53t8Wv. Source SHA-256: cde06a3d7e7439d271c39420bccc5ff3b936f2c1ea4c8754b0e6c1b49a6bf27d. Raw-description SHA-256: 0ce549658aa96676f398e1063aca03e7c0d49268b7f1dae2b5d71b7b92205c10.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
