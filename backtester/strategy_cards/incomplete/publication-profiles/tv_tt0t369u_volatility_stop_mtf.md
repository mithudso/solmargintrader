---

id: tv_profile_tt0t369u

name: "Volatility Stop MTF"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Volatility Stop MTF displays an ATR-based trend/stop reference from a selected higher timeframe and optionally detects chart-timeframe breaches before the higher trend changes. Early Breach distinguishes an exit warning from a trend reversal by marking a limbo state. This faster reaction can reduce waiting but can also leave the user out of much of a continuing trend, as the author explicitly explains."

registry_key: null

runner: null

evaluation: null

---

# Volatility Stop MTF

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volatility Stop MTF displays an ATR-based trend/stop reference from a selected higher timeframe and optionally detects chart-timeframe breaches before the higher trend changes. Early Breach distinguishes an exit warning from a trend reversal by marking a limbo state. This faster reaction can reduce waiting but can also leave the user out of much of a continuing trend, as the author explicitly explains.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Underlying ATR-stop recursion, length/multiplier defaults, comparison price and HTF confirmation rules are not reproduced.

- Underlying ATR-stop recursion, length/multiplier defaults, comparison price and HTF confirmation rules are not reproduced.

## How it works

- Calculate the inherited ATR-based stop on selected timeframe, then compare either chart bars or HTF information for breaches.
- Track limbo after an early breach until the underlying stop trend reverses and expose direction/breach alerts separately.

## Outputs and intended use

- Use the stop as a trend reference or discretionary exit context, with red early-breach triangles and optional limbo coloring.

## Parameters and stated settings

- Early Breach is default. HTF can be stepped, fixed or a fractional multiple such as 3.5; five alerts and two color themes are provided. Source recommends bar-close alerts.

## Failure modes and caveats

- Analytical: early breach can sacrifice continued trend exposure; source-stated default non-repainting mode still requires code/data timing verification.

## Missing information and implementation boundary

- Underlying ATR-stop recursion, length/multiplier defaults, comparison price and HTF confirmation rules are not reproduced.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
In the default, Early Breach mode
```

### E2: parameters, readiness

```text
3.5[/i] will work.
```

### E3: parameters, readiness

```text
Five pre-defined alerts
```

### E4: parameters, readiness

```text
Choice of 2 color themes.
```

### E5: mechanism, readiness

```text
state of [b]limbo
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_atr_trailing](../../tv_method_atr_trailing.md)
- [tv_tt0t369u_volatility_stop_mtf](../tv_tt0t369u_volatility_stop_mtf.md)

## Source

https://www.tradingview.com/script/tT0t369u-Volatility-Stop-MTF/

Publication ID: tT0t369u. Source SHA-256: 7ca7dba89162e8e70deeab3473d201d2af3baeacb68a5542f8e20faec35c2caa. Raw-description SHA-256: 044c76ea4ae851d52fb9947949261cec06c90b481ba92b504728e8f6e81fda5d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
