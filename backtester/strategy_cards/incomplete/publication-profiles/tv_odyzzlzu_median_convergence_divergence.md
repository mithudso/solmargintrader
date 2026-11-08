---

id: tv_profile_odyzzlzu

name: "Median Convergence Divergence"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Replace the central-tendency component of MACD with rolling medians to reduce the influence of extreme observations."

registry_key: null

runner: null

evaluation: null

---

# Median Convergence Divergence

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Replace the central-tendency component of MACD with rolling medians to reduce the influence of extreme observations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Median window parity convention, exact signal calculation, input price, divergence confirmation and execution timing are absent.

- Median window parity convention, exact signal calculation, input price, divergence confirmation and execution timing are absent.

## How it works

- Form a convergence/divergence oscillator from fast and slow median-based calculations and a signal line. The source contrasts a median's outlier resistance with a mean's sensitivity, without providing the complete signal smoothing formula.

## Outputs and intended use

- Use signal-line crosses, zero crosses and price/oscillator divergence analogously to MACD. The author recommends other indicators for actual entry/exit decisions.

## Parameters and stated settings

- Recommended daily periods are fast five, slow twenty, signal ten; weekly four/thirteen/eight; monthly three/twelve/six. Intraday settings should be customized.

## Failure modes and caveats

- Medians do not literally ignore every outlier and can respond abruptly when rank order changes. Threshold crossings and divergences are descriptive cues, not an independently complete risk plan.

## Missing information and implementation boundary

- Median window parity convention, exact signal calculation, input price, divergence confirmation and execution timing are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history; this establishes input class, not verified code, full history or profitability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
5 day period for the fast line, a 20 day period for the slow line, and a 10 day period for the signal line.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
4 week period for the fast line, 13 week period for the slow line, and 8 week period for the signal line.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
3 month period for the fast line, 12 month period for the slow line, and 6 month period for the signal line.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
When the MCD line crosses above the Signal line, it's a bullish crossover.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_odyzzlzu_median_convergence_divergence](../../tv_odyzzlzu_median_convergence_divergence.md)

## Source

https://www.tradingview.com/script/odyzZlzU-Median-Convergence-Divergence/

Publication ID: odyzZlzU. Source SHA-256: 43597e28e7d89e43dc7f1c7950b17ac3eb3602afd84d9566851cb7a0dada3572. Raw-description SHA-256: f12740351fc17f5a4972d624d4b443c331349b162e095004c556aec6fc9f4eae.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
