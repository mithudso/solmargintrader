---

id: tv_profile_wobqqsxf

name: "Black Scholes Option Pricing Model w/ Greeks [Loxx]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This options-model display estimates European-style option values and sensitivity measures from spot, strike, maturity, volatility, rates and dividends. Its purpose is theoretical valuation and exposure inspection, with selectable Greeks showing how model value changes when inputs move. It is not an option-chain feed or a guarantee of executable market prices; the source describes a work in progress and includes implementation wording that needs clarification."

registry_key: null

runner: null

evaluation: null

---

# Black Scholes Option Pricing Model w/ Greeks [Loxx]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This options-model display estimates European-style option values and sensitivity measures from spot, strike, maturity, volatility, rates and dividends. Its purpose is theoretical valuation and exposure inspection, with selectable Greeks showing how model value changes when inputs move. It is not an option-chain feed or a guarantee of executable market prices; the source describes a work in progress and includes implementation wording that needs clarification.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pricing approximation/iteration and Greek conventions are not specified despite the model name.

- Pricing approximation/iteration and Greek conventions are not specified despite the model name.

## How it works

- Apply a Black–Scholes–Merton-style model with carry/dividend inputs and compute selected price/input derivatives as Greeks.
- Use manual implied volatility, configurable time conventions and manual or automatic risk-free/dividend inputs; historical volatility is only a benchmark.

## Outputs and intended use

- Choose call/put and Greeks to inspect theoretical value and sensitivities to spot, volatility, time, rates, dividends and strike.

## Parameters and stated settings

- Daily timeframe only; source lists 18 Greeks and 33 spot-price sources. Calculation steps are capped at 300 despite discussing an iterative process for a normally closed-form model.
- Automatic rate uses a country ten-year bond yield; manual rates, dividend yield, expiry, days/year and hours/day are configurable.

## Failure modes and caveats

- Analytical: European lognormal-model assumptions, volatility smile and early-exercise effects can separate model from market value; yield maturity may not match option term.

## Missing information and implementation boundary

- Exact pricing approximation/iteration, Greek units, time basis defaults, automatic feed mapping and numerical safeguards are not disclosed.

## Data requirements

Required inputs: spot price, strike and expiry, implied volatility, risk-free rate, dividend yield.

Repository input-class support: unavailable or unresolved. Contract and model inputs plus optional external rate/dividend feeds are required; historical OHLCV does not supply implied volatility or contract terms.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
This can only be used on the daily timeframe
```

### E2: parameters, readiness

```text
contains 18 greeks.
```

### E3: parameters, readiness

```text
33 different types of price inputs
```

### E4: parameters, readiness

```text
this is limited to 300
```

### E5: parameters, readiness

```text
10 year bold yield
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wobqqsxf_black_scholes_option_pricing_model_w_greeks_loxx](../tv_wobqqsxf_black_scholes_option_pricing_model_w_greeks_loxx.md)

## Source

https://www.tradingview.com/script/WobQqSxF-Black-Scholes-Option-Pricing-Model-w-Greeks-Loxx/

Publication ID: WobQqSxF. Source SHA-256: 3812110b94462c00a7dd925ab55cda9bf54fd0eed38b622ab5e466f7bb1e9efb. Raw-description SHA-256: 400d0779f790c9f3249214250a05ee30aec03972c16b94f72d33d63309a76a0b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
