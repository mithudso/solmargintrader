---

id: tv_profile_hk4bwdkh

name: "Motion"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Motion provides animated string effects, with a price-ticker user interface as its explicit financial example. Its limited role is presentation infrastructure for a caller’s ticker text, not market analysis or signal generation. The source lists transition, marquee and hold interfaces plus keyframe state, but does not explain their full update semantics."

registry_key: null

runner: null

evaluation: null

---

# Motion

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: library. Review: independently reviewed.

## Idea and objective

Motion provides animated string effects, with a price-ticker user interface as its explicit financial example. Its limited role is presentation infrastructure for a caller’s ticker text, not market analysis or signal generation. The source lists transition, marquee and hold interfaces plus keyframe state, but does not explain their full update semantics.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** String-window algorithm, frame timing, state reset behavior, return types and caller financial-data contract are unspecified.

- String-window algorithm, frame timing, state reset behavior, return types and caller financial-data contract are unspecified.

## How it works

- Maintain keyframe sequence/interval/step/frame state and transform strings through marquee or transition effects, optionally holding a frame.

## Outputs and intended use

- Use animated text in a caller’s price-ticker display; financial values must come from the caller.

## Parameters and stated settings

- Interfaces expose substring length/start, whitespace/external-string controls and keyframe fields. No timing defaults or complete argument definitions are supplied.

## Failure modes and caveats

- Analytical: animation can display stale caller values or distract from relevant changes; the source’s memory-reduction claim is not independently measured.

## Missing information and implementation boundary

- String-window algorithm, frame timing, state reset behavior, return types and caller financial-data contract are unspecified.

## Data requirements

Required inputs: caller-provided ticker/price text, animation update events.

Repository input-class support: unavailable or unresolved. This consumes caller text/state rather than market OHLCV; no financial feed or actual text is supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, outputs_and_use, readiness

```text
Example: UI Price-Ticker
```

### E2: mechanism, readiness

```text
String-based transition-effects
```

### E3: parameters, readiness

```text
marquee(this, _extern, _ws, _subLen, _subStart)
```

## Source

https://www.tradingview.com/script/hk4bWDkH-Motion/

Publication ID: hk4bWDkH. Source SHA-256: 60f5ae1d634691698e474dee2aeeee5c7ecb4ae99b2d805699b0683f4016b4e5. Raw-description SHA-256: e10658808c917c0a9640955d967ce525a6ad9675f4842eb9ed94ba806a4bb6f8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
