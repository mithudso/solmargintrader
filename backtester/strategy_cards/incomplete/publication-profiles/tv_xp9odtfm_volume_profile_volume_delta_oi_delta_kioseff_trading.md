---

id: tv_profile_xp9odtfm

name: "Volume Profile Volume Delta OI Delta [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This profile estimates per-level volume delta and, for supported Binance perpetuals, open-interest delta. It distributes minute-bar activity across crossed price levels and optionally imposes a two-sided split when only one component appears. The goal is footprint-like visualization under limited data, with assumptions made explicit rather than a claim of true trade-by-trade aggressor volume."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile Volume Delta OI Delta [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This profile estimates per-level volume delta and, for supported Binance perpetuals, open-interest delta. It distributes minute-bar activity across crossed price levels and optionally imposes a two-sided split when only one component appears. The goal is footprint-like visualization under limited data, with assumptions made explicit rather than a claim of true trade-by-trade aggressor volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Unsigned equal-allocation minute-volume profile is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Divide one-minute volume/OI equally across the tick levels exceeded by the bar and append those contributions to level totals.
- Optionally replace one-sided recorded activity with an assumed buy/sell split and display labels/heatmaps.
- For each supplied one-minute bar find crossed caller-defined price levels. If k levels are crossed,add volume/k to each. Sum contributions over caller sample with explicit boundaries/spacing. This qualifies unsigned allocation;direction,OI,arbitrary60/40 and reset behavior remain excluded.

## Outputs and intended use

- Inspect level imbalances and OI changes, using optional timed recalculation and percentage/tick spacing.
- Usable scope: Unsigned equal-allocation minute-volume profile. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Optional split is 60/40 and is explicitly arbitrary. OI mode only supports Binance Futures; level spacing and recalculation threshold are user-defined.

## Failure modes and caveats

- Source warns unsupported OI assets prevent loading; analytical: equal allocation and arbitrary sides can materially misrepresent actual flow.

## Missing information and implementation boundary

- Original direction attribution, OI feed mapping, crossed-level boundary rules, reset/expiry and default spacing are unspecified.

## Data requirements

Required inputs: one-minute OHLCV, Binance perpetual OI history for OI mode.

Repository input-class support: unavailable or unresolved. Volume estimation can use minute data, but OI mode needs an external supported contract series and its mapping.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
assumes a 60/40 split
```

### E2: mechanism, readiness

```text
one-minute bar will be divided by the number of tick levels it exceeds.
```

### E3: parameters, risks, readiness

```text
only[/b] works for Binance Futures pairs
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
The script also divides volume and open interest if a one-minute bar violates multiple tick levels. The volume or open interest generated on the one-minute bar will be divided by the number of tick levels it exceeds. The results are, subsequently, appended to the violated tick levels.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
The script also divides volume and open interest if a one-minute bar violates multiple tick levels. The volume or open interest generated on the one-minute bar will be divided by the number of tick levels it exceeds. The results are, subsequently, appended to the violated tick levels.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_xp9odtfm_volume_profile_volume_delta_oi_delta_kioseff_trading](../tv_xp9odtfm_volume_profile_volume_delta_oi_delta_kioseff_trading.md)

## Source

https://www.tradingview.com/script/xp9OdTFm-Volume-Profile-Volume-Delta-OI-Delta-Kioseff-Trading/

Publication ID: xp9OdTFm. Source SHA-256: 97f77fe0468d7a8ce2d5b33fe5eb859b6b5dcbb01d7ea05002436a26ba5733b2. Raw-description SHA-256: 146d2b9bc32a0cd7e03a4c703f3aef5ad6dbe39e1226605a2254a17256d40d47.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
