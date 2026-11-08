---

id: tv_profile_jzxkmci2

name: "Williams Fractal Trailing Stops"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Williams Fractal Trailing Stops uses confirmed high and low fractals as moving protective references. Unlike a fixed confirmation convention, the user can choose how many bars establish a fractal. The indicator then trails those structural points and can switch between long and short orientation when price crosses the trail. Its purpose is stop monitoring rather than the broader Williams Alligator system, which the source explicitly excludes. Whether a stop reacts to an intrabar touch or a completed close is an important configurable difference for both timing and historical interpretation."

registry_key: null

runner: null

evaluation: null

---

# Williams Fractal Trailing Stops

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Williams Fractal Trailing Stops uses confirmed high and low fractals as moving protective references. Unlike a fixed confirmation convention, the user can choose how many bars establish a fractal. The indicator then trails those structural points and can switch between long and short orientation when price crosses the trail. Its purpose is stop monitoring rather than the broader Williams Alligator system, which the source explicitly excludes. Whether a stop reacts to an intrabar touch or a completed close is an important configurable difference for both timing and historical interpretation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Fractal-to-stop update/reset recurrence and crossing orientation are missing.

- Fractal-to-stop update/reset recurrence and crossing orientation are missing.

## How it works

- Detect Williams high/low fractals with configurable confirmation bars.
- Trail fractal levels and flip long/short when the selected price-crossing condition occurs.

## Outputs and intended use

- All fractal marks, a trailing stop line and long/short stop alerts support risk monitoring.

## Parameters and stated settings

- Fractal confirmation count and intrabar-versus-close flip policy are selectable; numeric defaults are absent.

## Failure modes and caveats

- Confirmed fractals arrive after their pivot and should not be treated as known at the pivot bar.
- Indicator alerts do not ensure fills at the plotted stop, especially through gaps.

## Missing information and implementation boundary

- Exact fractal equality rule, stop update/reset logic, initial direction, alert frequency and execution assumptions are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Fractal extrema and price-crossing tests are OHLCV-derived; no broker state is required by the described display.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
configure how many bars it takes to confirm a fractal.
```

### E2: outputs_and_use

```text
stop line that trails the fractals up and down.
```

### E3: parameters, mechanism

```text
within a candle or on candle close.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jzxkmci2_williams_fractal_trailing_stops](../tv_jzxkmci2_williams_fractal_trailing_stops.md)
- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/JZXkmCi2-Williams-Fractal-Trailing-Stops/

Publication ID: JZXkmCi2. Source SHA-256: be1c8f8706a66ea71c6d845f3ba9a6f2ccd554396a2f409aee9283261b56758c. Raw-description SHA-256: 00ba2421c06696783ceaca2b0f82ae875db285da1b1960dc99a5ae7e9972d83f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
