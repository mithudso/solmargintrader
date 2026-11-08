---

id: tv_profile_t1rsjdsb

name: "[UTILS] Session Input Parser"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: execution-tool

summary: "This session-input parser is companion infrastructure for scripts that accept a session-format string. It converts that configuration into individual start/end time and weekday fields, allowing a caller to consume the components instead of repeatedly parsing the string. It supplies no market signal or order permission by itself; the caller must define any trading-session logic."

registry_key: null

runner: null

evaluation: null

---

# [UTILS] Session Input Parser

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** execution-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This session-input parser is companion infrastructure for scripts that accept a session-format string. It converts that configuration into individual start/end time and weekday fields, allowing a caller to consume the components instead of repeatedly parsing the string. It supplies no market signal or order permission by itself; the caller must define any trading-session logic.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Return fields are documented but accepted session grammar and invalid/overnight parsing behavior are unspecified.

- Return fields are documented but accepted session grammar and invalid/overnight parsing behavior are unspecified.

## How it works

- Parse the supplied session string into starting hour/minute, ending hour/minute and an optional weekday array; return those components as a tuple.

## Outputs and intended use

- A calling script can use the returned time/day components in its own session configuration. Examples are stated to appear on the chart, but are not reproduced in the prose.

## Parameters and stated settings

- The documented input is sessionString. No default string or accepted-format examples appear in the description.

## Failure modes and caveats

- Analytical: parsing a configuration string does not validate that it matches a venue calendar, timezone or permitted execution session.

## Missing information and implementation boundary

- Supported session grammar, invalid-input behavior, overnight-session handling, timezone interpretation and any trading behavior of the caller are unspecified.

## Data requirements

Required inputs: caller-provided session-format string.

Repository input-class support: unavailable or unresolved. The caller must supply a session-format string; this is configuration input rather than chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, readiness

```text
An utility function to parse session inputs. Extracts hours, minutes and weekdays (if defined) and returns a tuple as the result.
```

### E2: parameters, mechanism, readiness

```text
_parseSession(sessionString) => (hourStart, minuteStart, hourEnd, minuteEnd, weekdaysArray)
```

## Source

https://www.tradingview.com/script/t1RSjDSb-UTILS-Session-Input-Parser/

Publication ID: t1RSjDSb. Source SHA-256: 57ae3360278817b98694c0968c19d0a96bf156176b7fbf32384c4db66d094fdb. Raw-description SHA-256: 411a641d2e001f653ba7ad6596457e6d7e2d8322ff1ef51f82a48f1d27a646dc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
