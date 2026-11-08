---

id: tv_profile_wvcqygsx

name: "MTF Oscillator Framework [PineCoders]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "MTF Oscillator Framework supplies an extensible chart/medium/high-timeframe presentation engine and includes a directional true-range oscillator as its financial example. Signed true range conveys directional volatility rather than volatility magnitude alone. The framework can aggregate horizons, identify nondirectional divergence levels and restrict bullish/bearish colors to selected conditions. It aims to help coders publish a complete configurable oscillator shell, but users still need a chosen signal and condition contract. The default aggregate repaints because its chart-timeframe component is allowed to develop."

registry_key: null

runner: null

evaluation: null

---

# MTF Oscillator Framework [PineCoders]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

MTF Oscillator Framework supplies an extensible chart/medium/high-timeframe presentation engine and includes a directional true-range oscillator as its financial example. Signed true range conveys directional volatility rather than volatility magnitude alone. The framework can aggregate horizons, identify nondirectional divergence levels and restrict bullish/bearish colors to selected conditions. It aims to help coders publish a complete configurable oscillator shell, but users still need a chosen signal and condition contract. The default aggregate repaints because its chart-timeframe component is allowed to develop.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for raw chart signed True Range (+TR up, −TR down, zero flat), exposed directly or through period1 ordinary smoothing. Full state predicates, aggregate/HTF timing and default repainting remain outside this scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent raw chart signal: use positive True Range for Close>Open, negative True Range for Close<Open, and zero for Close=Open even when range is nonzero. The instant value is exposed before averaging; choose chart-resolution output with smoothing period 1 and an ordinary supported average (neither Hull nor linear regression) to retain it.
- Calculate chart and two higher-timeframe versions and optionally weighted-average available components.
- Save oscillator levels when candle direction disagrees with signal slope; use subsequent relative position and additive filters for states.

## Outputs and intended use

- Three selectable lines, Donchian channel, divergence levels, bar-state markers/background, alerts and external BTE signal support analysis.

## Parameters and stated settings

- Seven smoothing types; period one gives raw signal except unsupported Hull/regression cases.
- Default group weights equal thirds; chart value repainting on and HTF repainting off.
- Auto-step example maps seconds charts to 15/60 minutes. Nine coloring conditions and eleven background choices are advertised.
- Narrow raw-signal path: chart timeframe, averaging period 1, no Hull or linear-regression smoothing, no HTF aggregate/state-engine dependency. The centerline is zero and units are price.

## Failure modes and caveats

- Historical behavior depends on HTF timing and changing early-history aggregate composition.
- Markers/alerts are configuration-dependent, and default chart signal can change.

## Missing information and implementation boundary

- All coloring predicates, auto-step table, smoothing defaults, ATR-filter lengths and HTF retrieval implementation are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The included signed-range signal and averages use OHLCV; arbitrary external signals require their own data contract.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
positive value of True Range
```

### E2: mechanism

```text
negative value is used when the bar is down
```

### E3: mechanism

```text
zero value is generated
```

### E4: parameters

```text
Seven different averages
```

### E5: parameters

```text
period of one
```

### E6: parameters

```text
15 and 60 minutes
```

### E7: parameters

```text
Nine different conditions
```

### E8: parameters

```text
11 different conditions
```

### E9: parameters

```text
equal weights for the three components
```

### E10: parameters, risks

```text
default is a repainting chart value
```

### E11: mechanism, readiness

```text
When a bar is up, the positive value of True Range is used. A negative value is used when the bar is down. When there is no movement during the bar, a zero value is generated, even if True Range is different than zero.
```

### E12: mechanism, parameters, readiness

```text
A period of one will show the instant value of the oscillator,
  provided you don't use linear regression or the Hull MA as they do not work with a period of one.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wvcqygsx_mtf_oscillator_framework_pinecoders](../tv_wvcqygsx_mtf_oscillator_framework_pinecoders.md)

## Source

https://www.tradingview.com/script/Wvcqygsx-MTF-Oscillator-Framework-PineCoders/

Publication ID: Wvcqygsx. Source SHA-256: 19d2e15c4e83774ca7c100336e2883e463a91159e5252da0fcbbcf44e41e06f5. Raw-description SHA-256: c6cfe1ae251ca4e9723da569319cf7d212b8aa31225334dc23a54b28405f85e3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
