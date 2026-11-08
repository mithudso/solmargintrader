---

id: tv_profile_ny63myd9

name: "Time & volume point of control / Flowly Indicators"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Show where each candle's strongest time occupancy and volume concentration occurred using lower-timeframe approximations."

registry_key: null

runner: null

evaluation: null

---

# Time & volume point of control / Flowly Indicators

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show where each candle's strongest time occupancy and volume concentration occurred using lower-timeframe approximations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The lower-timeframe selection map, maximum-volume source-price rule and ten-bracket close-count TPOC rule are explicitly stated. Tie handling is a nonblocking edge convention.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Choose the lower-timeframe bar with greatest volume and mark its selected price as VPOC. Divide the parent candle into ten price lots, count lower-timeframe closes in each and mark the midpoint of the most occupied lot as TPOC.

## Outputs and intended use

- Plot time as a line and volume as a dot, optionally replacing ordinary candle bodies with a range line. Concentration-threshold colors emphasize dominant observations. Suggested trapped-participant/trend narratives remain interpretations.

## Parameters and stated settings

- Default lower-timeframe map: chart <=30 minutes uses 1 minute; >30 minutes through 3 hours uses 5 minutes; >3 through 8 hours uses 15 minutes; >8 hours through 1 day uses 1 hour; >1 through 3 days uses 2 hours; >3 days uses 4 hours.
- Price source defaults to lower-timeframe close. Users can change source, interval and concentration thresholds. TPOC divides each candle range into ten price lots.

## Failure modes and caveats

- This VPOC is the price of the highest-volume sub-bar, not necessarily the true most-traded price. Finer data improves granularity but reduces accessible history and slows loading.

## Missing information and implementation boundary

- Tie resolution, missing sub-bars and exact treatment of boundary-equal closes are not supplied. No portfolio entry/exit process is specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed feature class; this does not establish implementation parity or complete data coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
For TPOC, each candle is divided into 10 lots
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
VPOC is defined by fetching lower timeframe candle with the most amount of volume traded and using its close (by default)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Charts <= 30 min: 1 minute timeframe
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Charts > 3D: 4 hour timeframe
```

### E5: mechanism, parameters, readiness

```text
Charts <= 30 min: 1 minute timeframe
Charts > 30 min & <= 3 hours : 5 minute timeframe
Charts > 3 hours & <= 8 hours : 15 minute timeframe
Charts > 8 hours & <= 1D: 1 hour timeframe
Charts > 1D & <= 3D : 2 hour timeframe
Charts > 3D: 4 hour timeframe
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_profile](../tv_method_market_profile.md)
- [tv_ny63myd9_time_volume_point_of_control_flowly_indicators](../../../strategy_research/tv_ny63myd9_time_volume_point_of_control_flowly_indicators.md)

## Source

https://www.tradingview.com/script/nY63MyD9-Time-volume-point-of-control-Flowly-Indicators/

Publication ID: nY63MyD9. Source SHA-256: dfbd0378ffedfb5582df02814dcedc901ba5efbbb8176ba52c7a74066f92554b. Raw-description SHA-256: 17d63dccd133e51682a409c916d03d84a6904f1416fb636307bd447533179f59.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
