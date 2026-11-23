---

id: tv_profile_jjgkjumy

name: "Live Economic Calendar by toodegrees"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Display planned and past economic-news times on price charts to support event awareness and historical review."

registry_key: null

runner: null

evaluation: null

---

# Live Economic Calendar by toodegrees

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Display planned and past economic-news times on price charts to support event awareness and historical review.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for fixed-width numeric decoding and scheduling supplied event times in their provided week/time convention; semantic code maps, DST/revision handling and actual feed acquisition remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Decode supplied non-sentinel event integers as fixed-width DCHHMMITYP: D one digit weekday, C one digit currency code, HH two digits hour, MM two digits minute, I one digit impact and TYP three digits event ID. Treat 999 as the empty-field placeholder. Each slot contributes up to five numeric events through its OHLCV fields.
- Encode calendar events as DCHHMMITYP integers across synthetic Pine Seeds OHLCV fields, using placeholder999. Spread events across nine slots, upload next week at dates rolled back one week and decode into an event array for tables/lines/labels.

## Outputs and intended use

- Filter by currency/impact and show chronological names, expected impact and times; grey past events. Upcoming lines are scheduling annotations, not predictions of market direction or realized volatility.

## Parameters and stated settings

- The described source covers January2007 onward, up to45 events/day using nine symbols/five fields. Original timezone is New York/EST and all-day events map to daily open. Lookback,week/day views and styling are adjustable.
- Nine slot identifiers are TOODEGREES_FOREX_FACTORY_SLOT_1, TOODEGREES_FOREX_FACTORY_SLOT_2, TOODEGREES_FOREX_FACTORY_SLOT_3, TOODEGREES_FOREX_FACTORY_SLOT_4, TOODEGREES_FOREX_FACTORY_SLOT_5, TOODEGREES_FOREX_FACTORY_SLOT_6, TOODEGREES_FOREX_FACTORY_SLOT_7, TOODEGREES_FOREX_FACTORY_SLOT_8 and TOODEGREES_FOREX_FACTORY_SLOT_9. Source time is 24-hour EST/New York; all-day events are marked at daily candle open.

## Failure modes and caveats

- The author recommends checking original sources and notes daily-chart omissions when markets close. Schedule revisions and historical backdating can make a reconstructed calendar differ from what was known at the time; live feed claims are unverified current.

## Missing information and implementation boundary

- Exact currency/event-ID mappings, timezone/DST conversion, feed access, revision-vintage retention and complete decoder/library rules are external or absent.

## Data requirements

Required inputs: Forex Factory event schedule, custom Pine Seeds encoded slot histories, event-ID/currency mappings.

Repository input-class support: unavailable or unresolved. An external calendar and custom maintained data feeds are essential; ordinary OHLCV cannot reconstruct them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
"DCHHMMITYP"
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
value "999" is used as a placeholder
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Nine unique symbols have been established, accommodating up to 45 news events per day.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
January 2007 to the present
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
roll-back date by one week
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
16:00 EST
```

### E7: mechanism, parameters, readiness

```text
Each news event is encoded as an integer in the "DCHHMMITYP" format.
D = day of the week
C = currency
HHMM = Time of day
I = news impact
TYP = event ID
```

### E8: mechanism, parameters, readiness

```text
the value "999" is used as a placeholder
```

### E9: mechanism, parameters, readiness

```text
TOODEGREES_FOREX_FACTORY_SLOT_N[/b]" where N ranges from 1 to 9.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)

## Source

https://www.tradingview.com/script/JjgkjuMY-Live-Economic-Calendar-by-toodegrees/

Publication ID: JjgkjuMY. Source SHA-256: 34b5846c8f6fd46742c9fbc3d4bfe2ca6fd5d6675163654d174dd93b6e5311e1. Raw-description SHA-256: 97c97059b4289c4d373abbea8f2dca204a57d6b54bdacb10232705e2dc81383e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
