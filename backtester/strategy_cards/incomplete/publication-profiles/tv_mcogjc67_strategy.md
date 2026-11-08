---

id: tv_profile_mcogjc67

name: "Strategy"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Provide strategy programmers with unit conversions, direction-aware exit levels, risk-based size helpers and a percentage-exit wrapper. These functions support a caller’s existing strategy and do not define an entry edge."

registry_key: null

runner: null

evaluation: null

---

# Strategy

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Provide strategy programmers with unit conversions, direction-aware exit levels, risk-based size helpers and a percentage-exit wrapper. These functions support a caller’s existing strategy and do not define an entry edge.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Percent-of-price and signed tick exit-level helpers is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Percentage conversions use average entry price or an explicit price; tick conversions connect instrument price units and currency amounts. Profit calculation evaluates a hypothetical exit relative to the active position.
- Stop and target helpers offset average entry by ticks and reverse direction for short positions. Position-size helpers target a fixed equity percentage using stop distance.
- exitPercent wraps a strategy exit with percentage loss/profit arguments and optional absolute or percentage exit quantities.
- For supplied price P and percentage p,percent amount=P*p/100. For supplied average entry E,tick size q,distance d>=0 and side s=+1 long/-1 short,stop=E-s*d*q,target=E+s*d*q. These helpers qualify independently from sizing rounding,currency/point-value conversions,absent-position behavior and pyramiding-sensitive exit wrapper.

## Outputs and intended use

- Returns ticks, price/currency values, percentage profit, stop/target levels and integer contract counts.
- The demonstration plots entry, stop and target levels and marks trades; levels may be passed into the caller’s exit orders.
- Usable scope: Percent-of-price and signed tick exit-level helpers. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Stop distance in ticks or percentage, equity risk percentage, entry/exit prices, order identifier, quantities, conditions and alert text.
- For exitPercent, qty defaults to na and the percentage quantity defaults to 100 when absolute quantity is absent.

## Failure modes and caveats

- The author warns that average-entry offsets may work incorrectly with pyramiding.
- Tick/currency/contract conversions need instrument point value, rounding and account currency treatment; incorrect assumptions would change risk. Stops do not guarantee realized loss during gaps.

## Missing information and implementation boundary

- Exact conversion formulas, contract rounding, point-value/currency handling and no-position/zero-stop behavior are not specified.

## Data requirements

Required inputs: strategy position direction average entry and equity, instrument tick size point value and currency metadata, caller stop/risk/order parameters.

Repository input-class support: unavailable or unresolved. Strategy runtime state and instrument contract metadata must be supplied; OHLCV alone does not provide them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The stop and take profit levels automatically flip sides based on whether the current position is long or short.
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
[b]calcPositionSizeByStopLossTicks(stopLossTicks, riskPercent)[/b]
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
this function may work incorrectly with pyramiding turned on
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The default value is `na`.
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
the default value of `qty_percent` is 100.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[b]percentToPrice(percent)[/b] Converts a percentage of the average entry price to a price.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[b]percentToCurrency(price, percent)[/b] Converts the percentage of a price to money.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[b]ticksToStopLevel(ticks)[/b] Calculates a stop loss level using a distance in ticks from the current `strategy.position_avg_price` entry price. This value can be plotted on the chart, or used as an argument to the `stop` parameter of a `strategy.exit()` call. NOTE: The stop level automatically flips based on whether the position is long or short.
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
[b]ticksToTpLevel(ticks)[/b] Calculates a take profit level using a distance in ticks from the current `strategy.position_avg_price` entry price.  This value can be plotted on the chart, or used as an argument to the `limit` parameter of a `strategy.exit()` call. NOTE: The take profit level automatically flips based on whether the position is long or short.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/mCOgJC67-Strategy/

Publication ID: mCOgJC67. Source SHA-256: 159ff212c51d4024648c4088cf8dc77972dafc75448a442c8a224c2fece2bd4b. Raw-description SHA-256: fd2d01ade4a0dd09a8880b3770a3f56619374382f09adfc5a685c1b3d69ac4be.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
