---

id: tv_profile_5eglveln

name: "Relative Bandwidth Filter"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Relative Bandwidth Filter identifies volatility regimes that another strategy can use to permit or suppress trading. It compares a broad channel width with a shorter-horizon ATR, then evaluates that ratio relative to its own Bollinger bands. The author explicitly interprets a high ratio as comparatively low volatility and a low ratio as comparatively high volatility, which should be preserved rather than replaced with an intuitive but different bandwidth interpretation."

registry_key: null

runner: null

evaluation: null

---

# Relative Bandwidth Filter

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Relative Bandwidth Filter identifies volatility regimes that another strategy can use to permit or suppress trading. It compares a broad channel width with a shorter-horizon ATR, then evaluates that ratio relative to its own Bollinger bands. The author explicitly interprets a high ratio as comparatively low volatility and a low ratio as comparatively high volatility, which should be preserved rather than replaced with an intuitive but different bandwidth interpretation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Parameterized relative bandwidth/Bollinger context is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Divide a selected channel bandwidth by ATR. Channel choices are Bollinger, Keltner or Donchian.
- Apply Bollinger bands to that relative-bandwidth series to determine whether its value is comparatively high or low.
- Choose a standard Bollinger, Keltner or Donchian channel and calculate bandwidth=upper-lower. Divide by built-in ATR of caller length. Apply standard Bollinger mean plus/minus caller-multiplier standard deviation to the ratio. Lengths/channel multipliers are caller parameters; directional Signal mapping is excluded.

## Outputs and intended use

- An unplotted Signal series is available through the data window and as another script’s external input. Values encode long-only, short-only, no trades or both directions.
- Usable scope: Parameterized relative bandwidth/Bollinger context. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Bandwidth length should exceed ATR length; no numeric defaults are supplied.
- Signal 1 allows long, -1 short, 0 no trades and 2 both sides.

## Failure modes and caveats

- Analytical: regime filtering cannot establish the profitability of the downstream strategy and may suppress useful trades.

## Missing information and implementation boundary

- The mapping from ratio/band states to directional Signal values, band settings and channel multipliers are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Relative Bandwidth = Bandwidth / ATR
```

### E2: parameters, readiness

```text
1 : Allow only Long
```

### E3: parameters, readiness

```text
-1 : Allow only short
```

### E4: parameters, readiness

```text
0 : Do not allow any trades
```

### E5: parameters, readiness

```text
2 : Allow both Long and Short
```

### E6: purpose, readiness

```text
If relative bandwidth is higher, then volatility is comparatively low.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[i]Relative Bandwidth = Bandwidth / ATR[/i]
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
Once we got Relative Bandwidth, the next step is to apply Bollinger Band on this to measure how relatively high/low this value is.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5eglveln_relative_bandwidth_filter](../tv_5eglveln_relative_bandwidth_filter.md)

## Source

https://www.tradingview.com/script/5egLveLn-Relative-Bandwidth-Filter/

Publication ID: 5egLveLn. Source SHA-256: e2c1e5a42a76a525bc7335788a15a0d8bea6c2ba351d7267c5ff8e6f5275eb4c. Raw-description SHA-256: 0e55208ae5dcff3f9fbcb2f2147f2fedd32c19af05227b882c35bd1c0d528514.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
