---

id: tv_profile_axtmvrud

name: "Fair Value Gap Profile + Rolling POC [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "FVG Profile + Rolling POC profiles where candle-gap formations concentrate, rather than simply where volume traded. It separates bullish and bearish gap counts and associated volume to describe directional imbalance by price region. A rolling peak/average and optional moving average add temporal context. The financial purpose is identifying repeated gap-formation zones for discretionary reaction analysis. Calling them inefficiencies does not prove an arbitrage opportunity or that price must revisit them. Several important mapping and rolling calculations remain conceptual rather than fully defined."

registry_key: null

runner: null

evaluation: null

---

# Fair Value Gap Profile + Rolling POC [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

FVG Profile + Rolling POC profiles where candle-gap formations concentrate, rather than simply where volume traded. It separates bullish and bearish gap counts and associated volume to describe directional imbalance by price region. A rolling peak/average and optional moving average add temporal context. The financial purpose is identifying repeated gap-formation zones for discretionary reaction analysis. Calling them inefficiencies does not prove an arbitrage opportunity or that price must revisit them. Several important mapping and rolling calculations remain conceptual rather than fully defined.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for raw bullish/bearish three-bar FVG events and their gap boundaries, supporting optional live boxes. Mitigation, profile mapping/volume, Rolling POC and Auto-MA equations remain outside this scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent three-bar FVG events: bullish when Low_t>High_(t−2), with raw gap boundaries [High_(t−2),Low_t]; bearish when High_t<Low_(t−2), with boundaries [High_t,Low_(t−2)]. These inequalities/boundaries define newly formed gaps independently of profile binning, volume assignment or later mitigation.
- Divide lookback price range into bins and assign each gap to its nearest bin; accumulate directional counts/volume.
- Normalize strength against the largest count and calculate an unspecified rolling peak-imbalance series with optional smoothing.

## Outputs and intended use

- Bull/bear profile segments, strength labels, delta/heatmap, live gap boxes and rolling POC/MA support zone analysis.

## Parameters and stated settings

- Strongest bin normalizes to 100%; lookback, bins, moving-average type/length and Auto scaling are configurable but defaults absent.
- Narrow raw-gap mode uses current and two-bars-back high/low with strict inequalities; live gap-box display is optional. The source supplies no additional raw-gap threshold or numeric defaults.

## Failure modes and caveats

- Gap-count density is not traded-volume density or actual resting liquidity.
- Moving bins and unspecified event-volume assignment can change apparent dominance.

## Missing information and implementation boundary

- Gap representative price, assigned volume, mitigation policy, rolling POC equation and Auto-length rule are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Three-candle gaps, volume and price bins use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
high two bars back is below the current low.
```

### E2: mechanism

```text
low two bars back is above the current high.
```

### E3: parameters

```text
strongest bin is normalized to 100%.
```

### E4: readiness

```text
moving average of where the market's most significant gaps are forming.
```

### E5: mechanism, parameters, readiness

```text
Bullish FVG: when the high two bars back is below the current low.
```

### E6: mechanism, parameters, readiness

```text
Bearish FVG: when the low two bars back is above the current high.
```

### E7: outputs_and_use, readiness

```text
Optionally plots individual bullish and bearish FVG boxes on the chart.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_axtmvrud_fair_value_gap_profile_rolling_poc_bigbeluga](../tv_axtmvrud_fair_value_gap_profile_rolling_poc_bigbeluga.md)
- [tv_method_fair_value_gap](../../../strategy_research/tv_method_fair_value_gap.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/axtmVrUD-Fair-Value-Gap-Profile-Rolling-POC-BigBeluga/

Publication ID: axtmVrUD. Source SHA-256: 3304ad2d247db6e4f8622c6563ff37066d4bf561e23320f532388d822e4ee8b5. Raw-description SHA-256: b0113c47ef1d8e840868fa3b6e93ba44e0bbbd1adb7448ae703d7e117a90ea55.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
