---

id: tv_profile_hnpilzeg

name: "Market Sessions - By Leviathan"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Market Sessions marks customizable trading windows and summarizes their price range or open-to-close movement. It aims to keep session context visible in boxes, zones, timelines or colored candles. Optional overlap merging truncates each session at the next session’s start, changing the effective measurement windows rather than merely hiding graphics. An open-to-current/close line and midpoint support directional and equilibrium inspection. The source promises correct default timezone behavior, but actual seasonal/session rules are not reproduced."

registry_key: null

runner: null

evaluation: null

---

# Market Sessions - By Leviathan

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Sessions marks customizable trading windows and summarizes their price range or open-to-close movement. It aims to keep session context visible in boxes, zones, timelines or colored candles. Optional overlap merging truncates each session at the next session’s start, changing the effective measurement windows rather than merely hiding graphics. An open-to-current/close line and midpoint support directional and equilibrium inspection. The source promises correct default timezone behavior, but actual seasonal/session rules are not reproduced.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for explicitly configured UTC session OHLC geometry, midpoint and open/close line. Missing default market windows and optional movement-label conventions do not block chosen sessions.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For caller-selected fixed-UTC session windows aligned to bar boundaries, collect session Open, running maximum High, running minimum Low and current/final Close. Equilibrium is (High+Low)/2. Draw the open-to-current-close line during the session and open-to-final-close when complete. Disable overlap merging for this narrow independent session geometry.
- Assign bars to configured session/timezone windows and collect high/low/open/close.
- Draw selected session forms and optional movement labels/midpoint.
- Optionally merge overlaps by ending each named session at the next start.

## Outputs and intended use

- Session boundaries, range/movement labels, direction line and half-range reference support contextual chart reading.

## Parameters and stated settings

- Four defaults Tokyo/London/New York/Sydney; times/names/colors, timezone, lookback, weekends and display controls configurable.
- Midpoint level0.5; lookback1 means one day. Description inconsistently lists four forms then three in settings.
- Specify UTC start/end windows and compatible chart bars; names/colors and lookback are selectable. Exact default windows, DST automation, percentage/pip calculations and partial-boundary bars remain caveats.

## Failure modes and caveats

- Session/DST conventions may differ from instrument hours.
- Merged windows change statistics and incomplete sessions use live price.

## Missing information and implementation boundary

- Default session times, DST handling, percentage denominator, pip-size convention and exact boundary treatment are absent.

## Data requirements

Required inputs: ohlcv, session/timezone configuration.

Repository input-class support: unavailable or unresolved. OHLCV supplies prices, but exact window/pip/timezone run contract is not specified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
4 market sessions
```

### E2: parameters

```text
0.5 level
```

### E3: parameters

```text
(1 = one day)
```

### E4: mechanism, readiness

```text
end of Tokyo is moved to start of London
```

### E5: mechanism, parameters, readiness

```text
input them in UTC
```

### E6: mechanism, parameters, readiness

```text
this will draw a line from the session open to the session close (or current price, if session is ongoing).
```

### E7: mechanism, parameters, readiness

```text
this will draw a horizontal line halfway between the session’s high and the session’s low.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hnpilzeg_market_sessions_by_leviathan](../../../strategy_research/tv_hnpilzeg_market_sessions_by_leviathan.md)

## Source

https://www.tradingview.com/script/hNpilzEG-Market-Sessions-By-Leviathan/

Publication ID: hNpilzEG. Source SHA-256: caae60c92c19a6fb55fdb0370b391f7628c9f75eea656764992735e4517893af. Raw-description SHA-256: 220b15e6f993bc54edbb36411f7b9c06c7468f3e45d53a897b4e0b2013f23da6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
