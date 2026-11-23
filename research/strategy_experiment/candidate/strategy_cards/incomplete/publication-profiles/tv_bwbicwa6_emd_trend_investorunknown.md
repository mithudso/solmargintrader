---

id: tv_profile_bwbicwa6

name: "EMD Trend [InvestorUnknown]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "EMD Trend builds a volatility-sensitive envelope from exponentially averaged absolute deviations around a chosen moving average. It aims to distinguish bullish/bearish excursions from neutral inside-channel behavior and provide trend/breakout context. Separate risk-on/off alerts identify crossings into and back out of outer regions. The optional historical performance mode is described as a diagnostic simulation with sizing and direction controls, but no fill/cost details are provided. Consequently the channel concept is clearer than either the persistent trend-state engine or the reported performance calculations."

registry_key: null

runner: null

evaluation: null

---

# EMD Trend [InvestorUnknown]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

EMD Trend builds a volatility-sensitive envelope from exponentially averaged absolute deviations around a chosen moving average. It aims to distinguish bullish/bearish excursions from neutral inside-channel behavior and provide trend/breakout context. Separate risk-on/off alerts identify crossings into and back out of outer regions. The optional historical performance mode is described as a diagnostic simulation with sizing and direction controls, but no fill/cost details are provided. Consequently the channel concept is clearer than either the persistent trend-state engine or the reported performance calculations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for caller-parameterized SMA/EMA-centered absolute-deviation EMA bands and explicitly named band-crossing events. Full FRAMA/state/backtest behavior remains incomplete.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow ordinary-MA envelope: choose source X and SMA or EMA center M with length L. Let D=EMA(|X−M|,K), Upper=M+mD and Lower=M−mD for selected deviation length K and multiplier m. Risk-on long is a price cross above Upper; risk-off long a cross back below Upper; risk-on short a cross below Lower and risk-off short a cross back above Lower. These are crossing events, not an inferred persistent trend-state machine.
- Calculate selected MA and EMA of absolute deviation from it, then multiply deviation for upper/lower bands.
- Classify excursions above/below bands and track corresponding trend flips/risk-on/off crossings.

## Outputs and intended use

- Colored bars/fills, channel states, six named alert categories and optional equity/statistics tables support trend research.

## Parameters and stated settings

- Seven MA types: SMA,EMA,HMA,DEMA,TEMA,RMA,FRAMA. Source, multiplier, intrabar option, start date, capital/trade percentage and long/short/both are configurable.
- Choose SMA/EMA, source, center length L, deviation EMA length K and multiplier m; numeric defaults are not supplied. FRAMA, intrabar repaint option, full trend-state persistence and backtest accounting are outside this scope.

## Failure modes and caveats

- Intrabar mode can repaint.
- Channel crosses in ranges can whipsaw; diagnostic equity does not establish achievable net returns.

## Missing information and implementation boundary

- MA/deviation lengths/defaults, FRAMA details, trend persistence/reset, fill/fee and metric equations are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. MA/deviation and volume-capable source calculations use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness, parameters

```text
exponential moving average of the absolute deviation from a moving average
```

### E2: parameters

```text
7 Moving Average Types
```

### E3: parameters, risks

```text
Intra-bar Signal Option
```

### E4: mechanism, parameters, readiness

```text
EMD Multiplier:
```

### E5: mechanism, parameters, readiness

```text
RISK-ON LONG - Price crosses above upper EMD band
```

### E6: mechanism, parameters, readiness

```text
RISK-OFF LONG - Price crosses back below upper EMD band
```

### E7: mechanism, parameters, readiness

```text
RISK-ON SHORT - Price crosses below lower EMD band
```

### E8: mechanism, parameters, readiness

```text
RISK-OFF SHORT - Price crosses back above lower EMD band
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bwbicwa6_emd_trend_investorunknown](../tv_bwbicwa6_emd_trend_investorunknown.md)

## Source

https://www.tradingview.com/script/bwbICwa6-EMD-Trend-InvestorUnknown/

Publication ID: bwbICwa6. Source SHA-256: 9835c680ee69e3ae4633ead803cf01506638f9528bc02e147538059b50ee04ce. Raw-description SHA-256: 8b21c6469f205925bf13eb099fb7756b3f28f2c36dcb922e1337cca79db9e1c5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
