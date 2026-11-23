---

id: tv_profile_wrheq9cf

name: "[e2] Drawing Library :: Horizontal Ray"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Provide reusable price-level rays that begin when a supplied condition occurs and monitor later retests."

registry_key: null

runner: null

evaluation: null

---

# [e2] Drawing Library :: Horizontal Ray

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Provide reusable price-level rays that begin when a supplied condition occurs and monitor later retests.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Touch definition, ray lifecycle across simultaneous levels, drawing limits, close/intrabar alert frequency and the historical-alert caveat's cause are not fully explained.

- Touch definition, ray lifecycle across simultaneous levels, drawing limits, close/intrabar alert frequency and the historical-alert caveat's cause are not fully explained.

## How it works

- The hray function starts a horizontal ray at a supplied level, extends it until price reaches it and optionally retains historical revisited levels. Alert delay validates a new level by suppressing alerts if it breaks too early.

## Outputs and intended use

- Callers can create rays from manual anchors, average crossovers or ATH events. The function returns no value and serves drawing/notification rather than a standalone trading strategy.

## Parameters and stated settings

- Extension and history default true; alert message defaults unavailable, delay zero, active style solid, historical style dashed and widths one. The examples include twenty/fifty-period average crosses with ten-bar validation delays.

## Failure modes and caveats

- The source warns to disable historical lines before creating alerts to avoid problems. A retest alert does not establish execution, and live touching behavior needs explicit confirmation.

## Missing information and implementation boundary

- Touch definition, ray lifecycle across simultaneous levels, drawing limits, close/intrabar alert frequency and the historical-alert caveat's cause are not fully explained.

## Data requirements

Required inputs: price history, caller condition and level.

Repository input-class support: available. Price data plus a caller-supplied event and level are sufficient input classes; no external feed is intrinsically required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default value true, current ray levels extend to the right
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
To avoid alert problems set to 'false' before creating alerts.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Default value int(0), number of bars to validate the level.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Default value int(1), ray width in pixels.
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
ta.​sma​(close, 20)
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data

```text
ta.​sma​(close, 50)
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data

```text
alert_delay = 10
```

## Source

https://www.tradingview.com/script/WRHeq9cf-e2-Drawing-Library-Horizontal-Ray/

Publication ID: WRHeq9cf. Source SHA-256: bebfd00cfe835976eba0a153e99f03deacedf5ecff300c1b18409d4167dffac3. Raw-description SHA-256: a9a11d688db6a455b26617434466010c8b9172846cb38a45399c7c9a25652472.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
