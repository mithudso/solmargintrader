---

id: tv_profile_85fu3jne

name: "Simple Trendlines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Manage conditional trendline drawing and continuation while optionally rejecting lines already violated before delayed pivot detection."

registry_key: null

runner: null

evaluation: null

---

# Simple Trendlines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Manage conditional trendline drawing and continuation while optionally rejecting lines already violated before delayed pivot detection.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The exported parameter contracts, example and strict side-test/linear continuation behavior specify a reproducible drawing computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Caller provides horizontal separation, endpoints, offset and draw/continue conditions. Extrapolate the initial line each update. Strict mode scans the delayed interval and requires all tested source values above or below the proposed line before accepting it.

## Outputs and intended use

- Return/manipulate line objects through an object interface. The example draws higher-pivot-low support with a ten-bar symmetric pivot and dashed styling; the library itself does not choose a trading entry.

## Parameters and stated settings

- Offset and strict mode/type are constructor options; strict types zero/one mean remain above/below. Strict mode requires positive offset. The example width is two, but full defaults are not enumerated.

## Failure modes and caveats

- The library does not support block-scoped execution. Caller-supplied endpoints and continuation policy determine whether a projected line represents valid structure; strict mode guards historical leakage relative to a line, not all forms of lookahead.

## Missing information and implementation boundary

- Exact optional defaults and boundary-equality behavior are not given. The specified linear geometry, offset handling and strict side checks nevertheless define its principal computation.

## Data requirements

Required inputs: caller endpoints, x distance and conditions, price/source history for strict checks.

Repository input-class support: available. Caller geometry and optional market source observations are sufficient; no external financial feed is intrinsically needed.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The distance between point A and point B provided by the user.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
0 - Ensures that all candles have closed above the trendline
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
1 - Ensures that all candles have closed below the trendline
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
input_len = input.int(defval = 10)
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Strict mode can only be used when the offset value is over 0.
```

## Source

https://www.tradingview.com/script/85fU3JnE-Simple-Trendlines/

Publication ID: 85fU3JnE. Source SHA-256: bdc2db7fd98918470e7bd184748a9c3c575daa9625b029b9120e0e9246020985. Raw-description SHA-256: 86079d7af4a0a09f18a0c782ed93706eac04e3f1ce3c327b31767ce3ee774e75.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
