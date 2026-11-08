---

id: tv_profile_eoijuoln

name: "Synthetic VX3! & VX4! continuous /VX futures"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Approximate continuous third- and fourth-month VIX futures to study farther-out volatility exposure when the charting platform lacks those continuous series."

registry_key: null

runner: null

evaluation: null

---

# Synthetic VX3! & VX4! continuous /VX futures

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Approximate continuous third- and fourth-month VIX futures to study farther-out volatility exposure when the charting platform lacks those continuous series.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Long-run level, mean-reversion speed fitting, contract calendar, roll adjustment and out-of-sample error measurements are absent.

- Long-run level, mean-reversion speed fitting, contract calendar, roll adjustment and out-of-sample error measurements are absent.

## How it works

- Combine spot VIX and front/second continuous VX futures with an exponential mean-reversion model toward a long-run level. The displayed formula is sigma(T)=theta+(sigma0-theta)exp(-kT).

## Outputs and intended use

- Compare synthetic farther-maturity histories against the front month for research or backtesting. These estimates are not actual historical contract prices or executable quotes.

## Parameters and stated settings

- The source names spot VIX, VX1! and VX2! as inputs but omits parameter calibration and maturity timing. It describes real-time subscription data or a fifteen-minute-delayed alternative.

## Failure modes and caveats

- The author informally expects roughly five-percent error and potentially worse behavior in backwardation; that is an unverified estimate, not measured validation. Continuous contract rolls can add further distortions.

## Missing information and implementation boundary

- Long-run level, mean-reversion speed fitting, contract calendar, roll adjustment and out-of-sample error measurements are absent.

## Data requirements

Required inputs: VIX spot history, VX1! and VX2! continuous futures histories.

Repository input-class support: unavailable or unresolved. Aligned volatility-index and futures histories require external feeds; the saved prose does not provide or verify them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
σ(T) = θ+(σ0−θ)e−kT
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
You can expect it to be off by ~5% or so (in times of backwardation it might be less accurate).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The indicator pulls actual realtime data (if you subscribe to the CBOE data package) or 15 minute delayed data for the VIX spot
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eoijuoln_synthetic_vx3_vx4_continuous_vx_futures](../tv_eoijuoln_synthetic_vx3_vx4_continuous_vx_futures.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/eoiJUoLN-Synthetic-VX3-VX4-continuous-VX-futures/

Publication ID: eoiJUoLN. Source SHA-256: e94fdea518f558b544aca9a959903854bebac6b598db875cec25d80cd33f3b7d. Raw-description SHA-256: 9bc0829bd25ce2faa135a78f8332eebdc44a41d90bc0e544542f73f8a03045ab.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
