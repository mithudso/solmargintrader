---

id: tv_profile_hxxk64fl

name: "SIP Evaluator and Screener [Trendoscope®]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Simulate recurring investment outcomes with commissions, fractional-unit rules and delayed dividend reinvestment, including screener-friendly output metrics."

registry_key: null

runner: null

evaluation: null

---

# SIP Evaluator and Screener [Trendoscope®]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Simulate recurring investment outcomes with commissions, fractional-unit rules and delayed dividend reinvestment, including screener-friendly output metrics.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for caller-scheduled basic contributions, commission deduction, fractional/whole-unit purchases, remainder and close-valued holdings; dividend-aware and corporate-action parity remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For the narrow non-dividend SIP, take each caller-scheduled contribution, deduct the chosen fixed commission or contribution times commission-percent, and add any carried remainder to purchasing cash. Divide by the selected OPEN/CLOSE/HL2/HLC3/OHLC4 reference to buy units, allowing fractions or rounding down to whole units; carry the unspent cash. Accumulate contributions, units and installment count, and value held units at the current close. Corporate-action and dividend reinvestment parity are separate.
- At each installment deduct fixed/percentage commission, buy units at a selected OHLC-derived price and carry unused cash when whole-unit mode applies. Track contributions separately from dividends/equity, optionally tax distributions and reinvest after a chosen delay.

## Outputs and intended use

- Plot invested amount, dividends,equity at closing price, remainder and installment count. The recommended monthly screener view compares selected stocks/funds under the same assumptions rather than placing purchases.

## Parameters and stated settings

- Defaults: start2020 with timebound false, contribution1000,fractional true,open purchases,commission3 fixed,tax disabled with rate47,dividend reinvestment enabled after2 bars. Dividend availability can use bars/weeks/months, with month30.5days.

## Failure modes and caveats

- Using close/high-low averages as purchase references can be non-executable; fund splits, total-return adjustments and dividend timing can double count returns if mismatched. General DCA benefit claims are not assured.

## Missing information and implementation boundary

- Dividend feed/adjustment contract, installment timing, same-bar reinvestment/commission ordering, day-vs-week availability and cross-symbol historical universe are not fully specified.

## Data requirements

Required inputs: OHLCV, dividend and corporate-action history, watchlist histories for screening.

Repository input-class support: unavailable or unresolved. Dividend-aware results require separate event data and adjusted-price conventions that the description does not supply.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Start Year (Default: 2020)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Timebound (Default: False)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Recurring Investment (Default: 1000.0)
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Allow Fractional Qty (Default: True)
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Price Reference (Default: OPEN)
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Commission (Default: 3)
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Commission Type (Default: Fixed)
```

### E8: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Dividend Tax (Default: 47)
```

### E9: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Reinvest Dividends After (Default: True, 2)
```

### E10: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
approximated as 30.5 days
```

### E11: mechanism, parameters, readiness

```text
only whole units are purchased (e.g., 2 shares), with any remaining funds carried forward as Remainder.
```

### E12: mechanism, parameters, readiness

```text
A flat fee is deducted per installment
```

### E13: mechanism, parameters, readiness

```text
A percentage of the investment amount is deducted as commission
```

### E14: mechanism, parameters, readiness

```text
current market value of the investment based on the closing price
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hxxk64fl_sip_evaluator_and_screener_trendoscope](../../../strategy_research/tv_hxxk64fl_sip_evaluator_and_screener_trendoscope.md)

## Source

https://www.tradingview.com/script/Hxxk64fl-SIP-Evaluator-and-Screener-Trendoscope/

Publication ID: Hxxk64fl. Source SHA-256: 8fb0f1f9ee81f0a39cb42b8f0d67c45acd481abe531a4b243388b4a0df44ee6d. Raw-description SHA-256: 7cd668848d066dd4a98081050cea315e4093a1cce506248d3bd2d977677aee77.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
