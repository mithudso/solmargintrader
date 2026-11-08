---

id: tv_profile_niy5oyf7

name: "Volume by Session"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Judge session volume against comparable sessions instead of mixing sessions with structurally different activity levels."

registry_key: null

runner: null

evaluation: null

---

# Volume by Session

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Judge session volume against comparable sessions instead of mixing sessions with structurally different activity levels.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact sessions/timezone, average weighting, overlap allocation and partial-session comparison rules are missing.

- Exact sessions/timezone, average weighting, overlap allocation and partial-session comparison rules are missing.

## How it works

- Separate volume by session and calculate each average using prior instances of that same session. Other sessions are excluded from its baseline.

## Outputs and intended use

- Compare the current London session with prior London sessions, for example, rather than with overlapping London/New York activity. A dark-screen display option changes presentation.

## Parameters and stated settings

- The example average spans five previous London sessions. The author states support up to one-hour charts and says the average line does not work below five minutes.

## Failure modes and caveats

- Session boundaries and daylight saving can change which observations are comparable. The source's broad claim about higher overlap-session volume is explanatory prose, not an established universal fact.

## Missing information and implementation boundary

- Exact sessions/timezone, average weighting, overlap allocation and partial-session comparison rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
the average on the london session is the average of the past 5 london sessions
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The indicator goes as high as 1H timeframe and the average line does not function below 5 mins
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_niy5oyf7_volume_by_session](../../../strategy_research/tv_niy5oyf7_volume_by_session.md)

## Source

https://www.tradingview.com/script/niY5OYf7-Volume-by-Session/

Publication ID: niY5OYf7. Source SHA-256: 9cf15df3457ae78451ac56f866ea00521d0245dd7598848428c427c32d123512. Raw-description SHA-256: e24eee6930bfb8d2d68ab0fcd3b18c5f8db73945a419b863c69d9adee3cddc83.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
