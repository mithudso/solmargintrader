---

id: tv_profile_ykinbu20

name: "True Close – Institutional Trading Sessions (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "True Close maps trading sessions and uses the close of each session’s first hour as a static price anchor. It emphasizes the transition into Sydney, Tokyo, London and New York with session boxes, opening-hour highlights and a dashboard. The author frames this as institutional closing logic, but the tool observes time and prices rather than actual institutional settlement or order completion."

registry_key: null

runner: null

evaluation: null

---

# True Close – Institutional Trading Sessions (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

True Close maps trading sessions and uses the close of each session’s first hour as a static price anchor. It emphasizes the transition into Sydney, Tokyo, London and New York with session boxes, opening-hour highlights and a dashboard. The author frames this as institutional closing logic, but the tool observes time and prices rather than actual institutional settlement or order completion.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** A caller-configured session start and timezone define the first-hour completed close anchor and range tracking; institutional interpretation and DST defaults are caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Detect configured session blocks, track each session range and separately highlight its first hour.
- Capture the first-hour close after completion, extend it as a reference and report session status and available anchor in a table.

## Outputs and intended use

- Inspect price rejection/breaks around the anchor and use the dashboard to distinguish active sessions from their opening phase.

## Parameters and stated settings

- Configurable UTC offset, session toggles, box/fill/border display, line/label styling and execution-hour labels. London 09:00–17:30 is an example, not a verified venue schedule.

## Failure modes and caveats

- Analytical: fixed offsets may mishandle daylight saving, and first-hour close is a user-defined analytical anchor rather than a universal institutional convention.

## Missing information and implementation boundary

- Complete session defaults/timezones, DST handling, missing bars and cross-session anchor expiration are unspecified.

## Data requirements

Required inputs: ohlcv, user-selected session/timezone configuration.

Repository input-class support: unavailable or unresolved. Price data supports the calculation, but exact session calendars and user timezone choices are needed for faithful reproduction.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
09:00–17:30 for London
```

### E2: mechanism, readiness

```text
The script captures the close of the first hour, not the end of the day.
```

### E3: parameters, readiness

```text
UTC Offset
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ykinbu20_true_close_institutional_trading_sessions_zeiierman](../tv_ykinbu20_true_close_institutional_trading_sessions_zeiierman.md)

## Source

https://www.tradingview.com/script/YkinBU20-True-Close-Institutional-Trading-Sessions-Zeiierman/

Publication ID: YkinBU20. Source SHA-256: e261585ee606c13ac62384aab1fbd3f9ddfddc45613217dd1689cf65312783d9. Raw-description SHA-256: 3a1f570757155303cccf09db310b6fe30157aea862aa5ca00550585aa257367c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
