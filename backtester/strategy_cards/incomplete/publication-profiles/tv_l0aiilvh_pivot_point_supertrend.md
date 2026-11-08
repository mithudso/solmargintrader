---

id: tv_profile_l0aiilvh

name: "Pivot Point Supertrend"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Pivot Point Supertrend replaces an ordinary price center with a smoothed average of pivots, then builds ATR bands around it. The intended benefit is holding trends longer by reducing sensitivity to minor price noise. Optional centerline and pivot-derived support/resistance add context, and the author suggests the centerline as an earlier partial-exit reference. Those examples express possible use rather than measured improvement. Buy/sell and reversal alerts are available, with an explicit recommendation to use bar-close alert frequency."

registry_key: null

runner: null

evaluation: null

---

# Pivot Point Supertrend

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Pivot Point Supertrend replaces an ordinary price center with a smoothed average of pivots, then builds ATR bands around it. The intended benefit is holding trends longer by reducing sensitivity to minor price noise. Optional centerline and pivot-derived support/resistance add context, and the author suggests the centerline as an earlier partial-exit reference. Those examples express possible use rather than measured improvement. Buy/sell and reversal alerts are available, with an explicit recommendation to use bar-close alert frequency.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pivot-center weighting recurrence and supertrend reversal computation are absent.

- Pivot-center weighting recurrence and supertrend reversal computation are absent.

## How it works

- Detect pivot points and average them with weight on past pivots for smoothing.
- Create upper/lower ATR bands around that center and derive supertrend behavior.
- Optionally show pivot-derived support/resistance and the centerline.

## Outputs and intended use

- Trend bands, pivot marks, centerline, support/resistance and entry/reversal alerts support trend following.

## Parameters and stated settings

- Pivot Point Period defaults to 2; example 4 is less sensitive.
- Visibility controls are optional; ATR settings/defaults are not given.
- Author suggests perhaps half-position early exits at centerline as a discretionary example.

## Failure modes and caveats

- Pivot confirmation introduces lag, while a longer-held trend can surrender gains.
- Source examples do not establish profitability or stop-fill quality.

## Missing information and implementation boundary

- Pivot equality/confirmation, exact weighting recurrence, ATR period/multiplier, reversal predicate and sizing rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Pivots, ATR and price crossings are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
calculating average of them
```

### E2: mechanism

```text
higher/lower bands by ATR.
```

### E3: parameters

```text
default value is 2
```

### E4: parameters

```text
PP period is 4
```

### E5: parameters, outputs_and_use

```text
maybe half of the position size
```

### E6: parameters

```text
Once Per Bar Close
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_l0aiilvh_pivot_point_supertrend](../tv_l0aiilvh_pivot_point_supertrend.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/L0AIiLvH-Pivot-Point-Supertrend/

Publication ID: L0AIiLvH. Source SHA-256: a48b5377369b08185ce9e8584a517a3305d275a7ec32971685f4d4a38cab3dcd. Raw-description SHA-256: 5dfd9fc79ca488724c898f4e49e02f9c7223c1785c0738d3c77462e132f41fb2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
