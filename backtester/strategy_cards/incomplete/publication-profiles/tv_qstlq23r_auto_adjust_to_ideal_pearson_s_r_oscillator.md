---

id: tv_profile_qstlq23r

name: "Auto Adjust To Ideal Pearson's R Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Show the correlation-strength behavior of an adaptive regression trend tool so short- and long-horizon trend confidence can be compared."

registry_key: null

runner: null

evaluation: null

---

# Auto Adjust To Ideal Pearson's R Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show the correlation-strength behavior of an adaptive regression trend tool so short- and long-horizon trend confidence can be compared.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Lookback search, white-state boundary, exact R inputs, companion synchronization and executable rules are not supplied.

- Lookback search, white-state boundary, exact R inputs, companion synchronization and executable rules are not supplied.

## How it works

- Plot long-term Pearson R in red and short-term R in green, with a white low-confidence state. The author uses an inverted directional convention: positive R means downtrend and negative R means uptrend.

## Outputs and intended use

- Coordinate the oscillator with the companion regression script using matching settings. Bottom green areas are described as buying zones and top red areas as potential shorting zones, without a complete entry/exit plan.

## Parameters and stated settings

- Ideal magnitude defaults to 0.85 and permitted trend lengths default to 48 through 360. Settings should match the companion tool.

## Failure modes and caveats

- The sign convention is implementation-specific and should not be mistaken for ordinary forward-time price correlation. Adaptive lookback choice can favor recent fit.

## Missing information and implementation boundary

- Lookback search, white-state boundary, exact R inputs, companion synchronization and executable rules are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
I set them to default to 0.85 for strong confidence levels.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*][b]+ Pearsons R means there is a downtrend[/b]
[*][b]- Pearsons R means there is an uptrend[/b]
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The default values are 48 and 360 for the minimum allowed length of a trend and maximum length.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qstlq23r_auto_adjust_to_ideal_pearson_s_r_oscillator](../tv_qstlq23r_auto_adjust_to_ideal_pearson_s_r_oscillator.md)

## Source

https://www.tradingview.com/script/qstlq23r-Auto-Adjust-To-Ideal-Pearson-s-R-Oscillator/

Publication ID: qstlq23r. Source SHA-256: 8932774fef9932a00fcb59978a1fdf343746284bf743e5cb7110de9efe5061fb. Raw-description SHA-256: 44e1b50e635587c494810f853e6c8a27b74ed7fd8e8bda8ff491de2445fe9123.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
