---

id: tv_profile_ulzjcb7h

name: "Volume by Time [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume by Time compares each bar with historical volume observed at the same time of day. It aims to distinguish an unusually active interval from a routine seasonal volume peak, instead of comparing all intraday bars indiscriminately. The historical benchmark can use a mean or median and either the whole available chart history or a selected number of days. The plotted relationship is contextual participation analysis and does not itself assign a trade direction."

registry_key: null

runner: null

evaluation: null

---

# Volume by Time [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume by Time compares each bar with historical volume observed at the same time of day. It aims to distinguish an unusually active interval from a routine seasonal volume peak, instead of comparing all intraday bars indiscriminately. The historical benchmark can use a mean or median and either the whole available chart history or a selected number of days. The plotted relationship is contextual participation analysis and does not itself assign a trade direction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines a parameterized aggregation without requiring trade rules.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Group observed bar volumes by the time of day at which the bars occurred.
- Aggregate each time group using the selected average or median, subject to the configured daily history window.

## Outputs and intended use

- Hollow histogram bars show the historical benchmark and solid columns current volume.
- The status line reports the number of analyzed days; optional bidirectional layout separates upward and downward volume visually.

## Parameters and stated settings

- Length Days defaults to 0, meaning all available history. Average is the default analysis type.
- Users can select median and enable bidirectional presentation.

## Failure modes and caveats

- Partial sessions can leave different sample counts at different offsets.
- Realtime current volume is incomplete until bar close; the display is not actual aggressor-side volume.

## Missing information and implementation boundary

- Timezone and optional up/down assignment details are not stated; the core time-group aggregation is explicit.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the default input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
volume of every bar is stored in groups organized by the time when each bar occurred.
```

### E2: outputs_and_use

```text
Hollow bars represent the average volume at that time of the day.
```

### E3: outputs_and_use

```text
Solid columns display the current volume from the current bar.
```

### E4: parameters

```text
Average (Default) or Median.
```

### E5: parameters

```text
Set to 0 for full data (Default 0).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ulzjcb7h_volume_by_time_luxalgo](../../tv_ulzjcb7h_volume_by_time_luxalgo.md)

## Source

https://www.tradingview.com/script/uLzJcB7H-Volume-by-Time-LuxAlgo/

Publication ID: uLzJcB7H. Source SHA-256: 194ea705553dec734d460147fe4c4447276a6c42eb68354cf82752cffcd58f5b. Raw-description SHA-256: fe426d412e916f25f8a71250b8289d997b54b7e17bad8c617e1883ce4c78f029.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
