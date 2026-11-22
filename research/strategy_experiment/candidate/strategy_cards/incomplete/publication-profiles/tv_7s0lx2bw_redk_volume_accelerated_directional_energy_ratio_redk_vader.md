---

id: tv_profile_7s0lx2bw

name: "RedK Volume-Accelerated Directional Energy Ratio (RedK VADER)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Estimate directional participation strength by combining close-to-close displacement with volume as an effort proxy."

registry_key: null

runner: null

evaluation: null

---

# RedK Volume-Accelerated Directional Energy Ratio (RedK VADER)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate directional participation strength by combining close-to-close displacement with volume as an effort proxy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The explanatory chain omits normalization, averaging and net-ratio equations required to reproduce the oscillator.

- Directional displacement normalization
- Volume accelerator and smoothing
- Net-energy equation

## How it works

- Combine price-change magnitude and volume acceleration, average positive and negative contributions separately and compute net directional energy. Full mode uses volume, Relative mode suppresses the lookback minimum and scales participation, and None mode removes volume with fallback when volume is absent.

## Outputs and intended use

- Blue/orange lines show buying/selling proxies and a green/red net line highlights zero crossings. The author says it is a secondary indicator requiring trend/momentum context.

## Parameters and stated settings

- Volume mode and a separate analysis timeframe are configurable. Relative accelerator is described as near zero for low volume and near one for high volume; exact lookbacks and averaging defaults are absent.

## Failure modes and caveats

- Directional energy is a trading analogy, not physics or observed investor identity. Volume sensitivity can distort the reading around session/auction spikes, and a zero cross is not a complete execution plan.

## Missing information and implementation boundary

- Displacement normalization, full/relative accelerator equations, smoothing, net-energy ratio and no-volume fallback formula are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class; code parity and cached-history coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
change of close between 2 bars
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
take an average of that relative energy in each direction
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
maximum volume accelerator (1 or close to 1)
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
VADER should be used as a *secondary indicator*
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7s0lx2bw_redk_volume_accelerated_directional_energy_ratio_redk_vader](../tv_7s0lx2bw_redk_volume_accelerated_directional_energy_ratio_redk_vader.md)

## Source

https://www.tradingview.com/script/7s0lx2Bw-RedK-Volume-Accelerated-Directional-Energy-Ratio-RedK-VADER/

Publication ID: 7s0lx2Bw. Source SHA-256: ddcfa0ac3c1f8e9fbfa6c09a4f250ce2b6ffd5ea32e9f31c8a1ac5b7584a5e0c. Raw-description SHA-256: a41cfb50dced92ac4b8c644f773a65f6735ccaf67cb92b180620f365c9d598ac.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
