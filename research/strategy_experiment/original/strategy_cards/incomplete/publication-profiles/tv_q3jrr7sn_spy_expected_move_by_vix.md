---

id: tv_profile_q3jrr7sn

name: "SPY Expected Move by VIX"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Translate VIX-implied uncertainty into an expected price-move envelope around SPY's volume-weighted average price."

registry_key: null

runner: null

evaluation: null

---

# SPY Expected Move by VIX

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Translate VIX-implied uncertainty into an expected price-move envelope around SPY's volume-weighted average price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The annualization basis, horizon conversion, VWAP reset, alignment and handling of missing VIX data are unspecified.

- The annualization basis, horizon conversion, VWAP reset, alignment and handling of missing VIX data are unspecified.

## How it works

- Use VIX as a proxy for SPY implied volatility over a thirty-day horizon and display one- and two-standard-deviation distances from VWAP. The time-scaling formula is not disclosed.

## Outputs and intended use

- Read the bands as volatility context for SPY. The author allows correlated instruments but says the indicator is meaningful principally for SPY.

## Parameters and stated settings

- The disclosed bands are one and two standard deviations; VWAP anchoring and VIX conversion settings are absent.

## Failure modes and caveats

- VIX is a proxy derived from index options, so using it for another instrument introduces basis risk. A standard-deviation label does not guarantee realized containment probabilities.

## Missing information and implementation boundary

- The annualization basis, horizon conversion, VWAP reset, alignment and handling of missing VIX data are unspecified.

## Data requirements

Required inputs: SPY intraday price/volume, VIX implied-volatility series.

Repository input-class support: unavailable or unresolved. The feature requires aligned SPY and VIX data; those external series are not supplied or verified here.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This indicator shows 1 and 2 standard deviation price move from the VWAP based on VIX.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
VIX is used as a proxy for SPY's IV for 30 days.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_vix_timing](../tv_method_vix_timing.md)
- [tv_q3jrr7sn_spy_expected_move_by_vix](../tv_q3jrr7sn_spy_expected_move_by_vix.md)

## Source

https://www.tradingview.com/script/Q3jRR7sN-SPY-Expected-Move-by-VIX/

Publication ID: Q3jRR7sN. Source SHA-256: 1d5f8175794f2a9bc7ff903627884a04d975a6c62ff1966c36c1478e4689217f. Raw-description SHA-256: cd3e0ed86a8e6e84d202a4664a0740b96d57c297f0f670b24634b4a419911c9e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
