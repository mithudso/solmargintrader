---

id: tv_profile_yyrxrhi9

name: "ATR Rope"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Separate movement beyond an ATR-sized tolerance from smaller noise and preserve reference zones formed while the filtered center stays flat."

registry_key: null

runner: null

evaluation: null

---

# ATR Rope

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Separate movement beyond an ATR-sized tolerance from smaller noise and preserve reference zones formed while the filtered center stays flat.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the excess-distance rope-center recurrence with caller-supplied ATR tolerance, source and starting rope; exact published initialization and consolidation-zone lifecycle remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For selected source S, previous rope R and supplied ATR tolerance A, leave R fixed while S is within [R-A,R+A]. When S exceeds the upper boundary, shift R upward by S-(R+A); below the lower boundary, shift it down by (R-A)-S. Thus the rope moves only by the distance beyond its tolerance envelope.
- Color upward rope motion green and downward motion red; a source crossing of the rope turns it blue/flat. Optional channel bounds are rope plus/minus ATR. During flat areas the upper/lower observations are accumulated and averaged into consolidation zones, whose exact lifecycle is not fully specified.

## Outputs and intended use

- Use rope, optional ATR bounds and extending zones to interpret trends, consolidation and retests. The author explicitly says it supplies no complete signal system.

## Parameters and stated settings

- Source is caller-selected, illustrated by separate high/low instances. ATR channel is hidden by default. The narrow recurrence accepts a supplied ATR series and initial rope value; published ATR length/estimator and seed defaults are not specified.

## Failure modes and caveats

- The source claims live-drawn zones do not repaint, but unavailable code prevents verification. ATR changes and developing bars can shift boundaries; visual retests do not define executable setups.

## Missing information and implementation boundary

- ATR estimator/defaults, rope initialization, exact flat-state reset and zone accumulation/end rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; code parity and historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Adjusting the rope when price extends past the threshold created by +/- ATR from the rope.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
When the source crosses the rope, it turns blue (flat).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
upper and lower values are accumulated and averaged together
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
by default it is hidden.
```

### E5: mechanism, parameters, readiness

```text
When the source moves beyond this range, the rope is adjusted based on the distance from the source to the channel.
```

### E6: mechanism, parameters, readiness

```text
When the rope's value moves up, it changes to green (uptrend), when down, red (downtrend).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_atr_trailing](../../tv_method_atr_trailing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_yyrxrhi9_atr_rope](../../tv_yyrxrhi9_atr_rope.md)

## Source

https://www.tradingview.com/script/YYrxRhi9-ATR-Rope/

Publication ID: YYrxRhi9. Source SHA-256: a86600f8b716da904b99c053a9902e0c42ba65f332e085459afdab91acd7d5e9. Raw-description SHA-256: dcb4c9f8e0b230d70c6ef744b757797d15cb2ac8bf99bf800bfc70007869b41a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
