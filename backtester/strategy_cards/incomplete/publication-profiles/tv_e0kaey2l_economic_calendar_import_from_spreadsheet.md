---

id: tv_profile_e0kaey2l

name: "Economic Calendar (Import from Spreadsheet)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Economic Calendar Import from Spreadsheet places vertical event-time markers on a chart from user-supplied text. It aims to remove repetitive manual drawing and align important scheduled announcements precisely with chart time. The user remains responsible for choosing relevant events and formatting their timestamps; the script is not described as an automatic live calendar feed. Its financial use is event-risk awareness, potentially helping a trader interpret price behavior near announcements or avoid unplanned exposure. No impact-scoring model or event-driven entry rule is supplied."

registry_key: null

runner: null

evaluation: null

---

# Economic Calendar (Import from Spreadsheet)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Economic Calendar Import from Spreadsheet places vertical event-time markers on a chart from user-supplied text. It aims to remove repetitive manual drawing and align important scheduled announcements precisely with chart time. The user remains responsible for choosing relevant events and formatting their timestamps; the script is not described as an automatic live calendar feed. Its financial use is event-risk awareness, potentially helping a trader interpret price behavior near announcements or avoid unplanned exposure. No impact-scoring model or event-driven entry rule is supplied.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The timestamp string schema, timezone prefix and one-vertical-line-per-event transformation define the economic-calendar drawing. Optional event metadata, parser validation and the erroneous prose date example do not block that principal output.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Parse a timezone and semicolon-separated event datetimes from an input string.
- Draw a vertical line at each parsed timestamp using configured style settings.
- An optional shared spreadsheet template formats raw calendar data before manual input.

## Outputs and intended use

- Event lines mark scheduled economic announcements on the price chart.

## Parameters and stated settings

- Source Data string, line color and line width are inputs.
- Datetime fields use YYYY,MM,DD,hh,mm,ss with a leading timezone.

## Failure modes and caveats

- The example’s prose says June 6 although its supplied timestamps identify different dates, so source examples should be checked.
- Stale or mis-zoned user input can mark the wrong event time; no automatic refresh is established.

## Missing information and implementation boundary

- Parser validation, duplicate handling, event names/impact metadata, rescheduling behavior and defaults are absent.

## Data requirements

Required inputs: user-selected economic event timestamps and timezone.

Repository input-class support: unavailable or unresolved. Requires an external curated event schedule; price candles do not supply scheduled announcements.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, outputs_and_use

```text
draws vertical lines to mark Economic Calendar Events.
```

### E2: mechanism, required_data, readiness

```text
Datetime of events is defined by user in Settings
```

### E3: parameters

```text
YYYY,MM,DD,hh,mm,ss
```

### E4: risks

```text
June 6, 2022
```

## Source

https://www.tradingview.com/script/E0KaEY2L-Economic-Calendar-Import-from-Spreadsheet/

Publication ID: E0KaEY2L. Source SHA-256: 5144a06f885392eb3a69c60fce50dc7690983f0a30b1942c6aa597a77c0272b2. Raw-description SHA-256: 00aba0327dc341bf69feb77ba74869c5e3abf13f362403a7c1f856db2c162e10.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
