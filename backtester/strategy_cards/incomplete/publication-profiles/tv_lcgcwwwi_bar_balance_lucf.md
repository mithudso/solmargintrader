---

id: tv_profile_lcgcwwwi

name: "Bar Balance [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Count bullish,bearish and unchanged lower-timeframe candles inside historical parent bars and summarize their relative balance as participation-strength context."

registry_key: null

runner: null

evaluation: null

---

# Bar Balance [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Count bullish,bearish and unchanged lower-timeframe candles inside historical parent bars and summarize their relative balance as participation-strength context.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for raw up/down/neutral intrabar counts and stacked columns on supplied partitions; historical-only behavior, auto-resolution and derived balances remain limitations.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Given supplied intrabar partitions count U where close>open, D where close<open and N where close=open. Neutral spans -N/2..N/2, Up N/2..N/2+U and Down -N/2-D..-N/2. These raw stacked counts are independent of optional balance/momentum/auto-resolution modes.
- Classify intrabars by close versus open. Draw stacked counts or derive instant balance,EMA up-minus-down balance,RSI-normalized momentum of EMA-versus-double-period-SMA differences,marker-bias counts and aggregate balance votes. Optional neutral-ratio damping and later-intrabar weighting alter the line.

## Outputs and intended use

- Columns,line/fill/zero-line colors,divergence levels and six marker types show different count-based contexts. The source explicitly works only on historical bars,requires recalculation to reveal elapsed live bars and provides no reliable alerts or automated trading use.

## Parameters and stated settings

- Auto modes target about12 or24 intrabars,or manual resolution. Listed calculation defaults are balance averages50,momentum20,dual averages20,marker bias10,but an earlier paragraph says marker bias default14. Neutral-count divergence threshold exceeds50%.
- Supported parent resolutions: 3,5,10,15,30 minutes; 1,2,4,6,12 hours; 1 day,1 week,1 month. Parent resolution must be divisible by intrabar resolution. These are source-stated historical constraints.

## Failure modes and caveats

- Intrabar direction counts ignore magnitude and volume; one large move can dominate many small opposite candles. Divergence is an anomaly/context marker,not a guaranteed reversal. Historical-only security behavior and runtime limits constrain use.

## Missing information and implementation boundary

- Instant balance ratio,momentum aggregation/RSI periods,neutral damping modes,marker-bias default contradiction,auto-step mappings and divergence-level recurrence are missing.

## Data requirements

Required inputs: lower-timeframe OHLC history.

Repository input-class support: available. Historical lower-timeframe OHLC is the input class; no actual traded-volume or external universe is intrinsically required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, risks, readiness

```text
works on historical bars only.
```

### E2: purpose, mechanism, parameters, risks, readiness

```text
close > open
```

### E3: purpose, mechanism, parameters, risks, readiness

```text
close < open
```

### E4: purpose, mechanism, parameters, risks, readiness

```text
close = open
```

### E5: purpose, mechanism, parameters, risks, readiness

```text
average minimum of 12 intrabars
```

### E6: purpose, mechanism, parameters, risks, readiness

```text
average minimum of 24 intrabars
```

### E7: purpose, mechanism, parameters, risks, readiness

```text
Balance Averages: 50
```

### E8: purpose, mechanism, parameters, risks, readiness

```text
Balance Momentum: 20
```

### E9: purpose, mechanism, parameters, risks, readiness

```text
Dual Up/Down Averages: 20
```

### E10: purpose, mechanism, parameters, risks, readiness

```text
Marker Bias: 10
```

### E11: purpose, mechanism, parameters, risks, readiness

```text
the default is 14
```

### E12: purpose, mechanism, parameters, risks, readiness

```text
greater than 50%
```

### E13: mechanism, parameters, readiness

```text
"Up" section represents the count of intrabars where `close > open`, "Down" where `close < open` and "Neutral" where `close = open`.
```

### E14: mechanism, parameters, readiness

```text
The Neutral section overlaps the centerline, split halfway above and below it.
```

### E15: mechanism, parameters, readiness

```text
3, 5, 10, 15 and 30 minutes, 1, 2, 4, 6, and 12 hours, 1 day, 1 week and 1 month.
```

### E16: mechanism, parameters, readiness

```text
chart resolutions must be divisible by the lower resolution used for intrabars
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lcgcwwwi_bar_balance_lucf](../../tv_lcgcwwwi_bar_balance_lucf.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)

## Source

https://www.tradingview.com/script/lcgCwWwI-Bar-Balance-LucF/

Publication ID: lcgCwWwI. Source SHA-256: 0ee6ed806b81d7bb5f7c0b579af94f4a7a370d9d3338f0c3b2a6e181b80e3057. Raw-description SHA-256: 5d0fab33955050c89004b791ee09767db3ff01f9e028fc028727c2a405e2f44e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
