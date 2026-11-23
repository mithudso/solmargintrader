---

id: tv_profile_ysff2otq

name: "LibraryCOT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Construct platform ticker identifiers for Commitment of Traders futures reports. LibraryCOT hides the encoding and asset/report mapping behind helpers so programmers can request positioning series; it does not generate a trading signal or interpret positioning."

registry_key: null

runner: null

evaluation: null

---

# LibraryCOT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Construct platform ticker identifiers for Commitment of Traders futures reports. LibraryCOT hides the encoding and asset/report mapping behind helpers so programmers can request positioning series; it does not generate a trading signal or interpret positioning.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Complete root/currency and metric-code lookup tables are not provided in text; exact subtype suffix and validation implementation remain absent.

- Complete root/currency and metric-code lookup tables are not provided in text; exact subtype suffix and validation implementation remain absent.

## How it works

- Helpers translate a futures root or currency to CFTC commodity codes, encode options inclusion, map metric/direction and encode report subtype. The full builder combines these into a COT ticker string.
- Automatic asset resolution tries root, then base currency, then quote currency; callers can instead choose one explicitly or return the raw symbol identifier.
- Legacy, Disaggregated and Financial reports expose different trader categories, position/trader counts and concentration metrics with applicable long/short/spreading/no-direction combinations. Invalid choices can raise runtime errors.

## Outputs and intended use

- Functions return mapping components or complete requestable ticker strings. A demonstration table shows supported metric/direction combinations.
- Downstream callers must fetch data and design their own positioning comparisons, including respecting publication timing.

## Parameters and stated settings

- Report family, six-digit CFTC code, options inclusion, metric name/direction and All/Old/Other subtype.
- convertToCOT defaults true; Auto uses the stated resolution priority.

## Failure modes and caveats

- The prose’s example says a futures-only encoding is “without futures,” contradicting its F/FO definitions; preserve the encoding definition rather than infer asset coverage.
- COT series are weekly and published after the positioning observation date; point-in-time use requires release dates and revisions. Historical API references may be stale.

## Missing information and implementation boundary

- Complete root/currency and metric-code lookup tables are not provided in text; exact subtype suffix and validation implementation remain absent.

## Data requirements

Required inputs: CFTC root currency and metric lookup mappings, caller symbol and report parameters, external COT report history and release timestamps.

Repository input-class support: unavailable or unresolved. Requires CFTC/report metric mappings, symbol metadata and external COT history; these are not supplied by OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
"Auto": the function tries the first three modes (Root -> Base Currency -> Currency) until a match is found.
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
"FO" for data that includes options and "F" for data that doesn't.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Optional. The default is `true`.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
A ticker ID string usable with `request.security()` to fetch the specified Commitment of Traders data.
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Is a six digit code that represents a commodity.
```

## Source

https://www.tradingview.com/script/ysFf2OTq-LibraryCOT/

Publication ID: ysFf2OTq. Source SHA-256: c2d7a0f201a778800917e6be33e25813083d0c9aa428e67aeaf205741eb2dcb4. Raw-description SHA-256: 83f8a2613995d2e2c0983bf78772a39e84969fb1a3cab6da230f35d52e6e7d74.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
