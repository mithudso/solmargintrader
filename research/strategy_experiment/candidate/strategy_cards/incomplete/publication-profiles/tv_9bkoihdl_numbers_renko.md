---

id: tv_profile_9bkoihdl

name: "Numbers Renko"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Numbers Renko annotates Renko boxes with volume and elapsed-time information to support Wyckoff-style effort-versus-result reading. It helps distinguish a box requiring unusually large activity or time from an ordinary box, and aggregates volume into Weis waves for comparison with earlier waves. The author explicitly limits exact operation to Renko charts. The display therefore depends on synthetic brick construction, not just ordinary time candles. It is a discretionary market-structure aid; a large effort/no-result mark is not by itself a specified reversal entry."

registry_key: null

runner: null

evaluation: null

---

# Numbers Renko

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Numbers Renko annotates Renko boxes with volume and elapsed-time information to support Wyckoff-style effort-versus-result reading. It helps distinguish a box requiring unusually large activity or time from an ordinary box, and aggregates volume into Weis waves for comparison with earlier waves. The author explicitly limits exact operation to Renko charts. The display therefore depends on synthetic brick construction, not just ordinary time candles. It is a discretionary market-structure aid; a large effort/no-result mark is not by itself a specified reversal entry.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable narrowly for per-brick volume/time baseline comparisons, large-value filtering and relative color categories, given an external Renko sequence. Weis-wave segmentation, exact threshold equality and brick construction remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Given a supplied Renko sequence with brick volume V and elapsed time T, compute the user-period EMA baseline for each (SMA is selectable). Compare V or T with its corresponding baseline. Show-only-large mode retains values strictly above their baseline. Colors use successively larger relative categories: at most half baseline, above half, above one, above 1.5 and above two times baseline; the source does not fully settle equality at the higher boundaries.
- Accumulate Weis Wave Volume and divide it by wave length to estimate effort per brick.
- Compare current waves with preceding same/opposite-direction waves and flag unusually high effort or volume.

## Outputs and intended use

- Numbers inside boxes, configurable candle colors, arrows and square marks expose relative volume/time and wave effort.

## Parameters and stated settings

- EMA is the default averaging type, with SMA available; period and volume display divisor are configurable.
- Relative-volume color categories include above 2x, 1.5x, 1x and 0.5x average.
- No Result Ratio compares effort with its five-period SMA; Large Volume Ratio controls wave highlighting.
- Per-brick comparison takes the caller-selected average period and EMA/SMA choice; no default period is supplied. Volume and elapsed time may independently drive number and candle colors.

## Failure modes and caveats

- Renko brick path, volume allocation and elapsed time depend on feed and brick settings.
- The divisor example inconsistently writes 0.056 and 0.05, so its exact display arithmetic should not be inferred from prose.

## Missing information and implementation boundary

- Brick construction, wave reversal rule, default periods/ratios and complete trade rules are absent.

## Data requirements

Required inputs: Renko brick sequence with volume and elapsed time.

Repository input-class support: unavailable or unresolved. Ordinary OHLCV does not establish the exact synthetic brick path or allocated per-brick time/volume.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: required_data, risks

```text
only works exactly in Renko Chart.
```

### E2: parameters

```text
2 times larger than the ARV
```

### E3: parameters

```text
1.5 times larger than the ARV
```

### E4: parameters

```text
larger than half
```

### E5: parameters, mechanism, readiness

```text
AEvsR is calculated by 5SMA.
```

### E6: mechanism

```text
Weis Wave Volume divided by Wave Length.
```

### E7: mechanism, readiness

```text
Show Only Large Renko Volume : show only Renko Volume which is larger than Average Renko Volume
```

### E8: parameters, mechanism

```text
Default is EMA, You can choice SMA.
```

### E9: mechanism, readiness

```text
Color1 If the current Renko Volume is larger than the ARV . Color0.5 is larger than half Athe RV and Color0 is  less than or equal to half the ARV.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9bkoihdl_numbers_renko](../tv_9bkoihdl_numbers_renko.md)
- [tv_method_renko](../tv_method_renko.md)
- [tv_method_volume_spread_analysis](../tv_method_volume_spread_analysis.md)
- [tv_method_wyckoff](../tv_method_wyckoff.md)

## Source

https://www.tradingview.com/script/9BKOIhdl-Numbers-Renko/

Publication ID: 9BKOIhdl. Source SHA-256: b3e3ee33c2479356d236fc5a51044ef06d9d227ae8b9fc6277ad1457f165e1cc. Raw-description SHA-256: 3963c1d80829612fa469cc6939931619b7d7d4a975334720a9bc9b8acceaf7b3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
