---

id: tv_profile_tpseizhp

name: "Volume X-ray [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Diagnose differences between historical intraday and end-of-day volume reporting. Volume X-ray helps identify instruments whose feeds deserve investigation; the author explicitly leaves the reporting cause and interpretation to the user."

registry_key: null

runner: null

evaluation: null

---

# Volume X-ray [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Diagnose differences between historical intraday and end-of-day volume reporting. Volume X-ray helps identify instruments whose feeds deserve investigation; the author explicitly leaves the reporting cause and interpretation to the user.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The historical feed-volume ratio is defined by the disclosed aggregation and division; no trading rule is required for this diagnostic.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Aggregate minute-feed volume across each day and compare it with the corresponding end-of-day volume. The publication describes the historical platform distinction between a minute-count daily request and a daily-code request.
- Display daily volumes and the cumulative intraday-to-EOD percentage across the loaded dataset. Gapped requests allow accumulation of available daily observations; missing values receive special handling.
- Only historical bars participate. The script rejects charts above daily resolution because lower-timeframe retrieval there would produce misleading daily fragments.

## Outputs and intended use

- Teal EOD area, orange intraday line, Data Window values and a percentage badge expose feed discrepancies.
- Badge color changes at half-volume coverage, while yellow flags abnormal/missing volume. Higher coverage is only an explicitly unproven reliability heuristic.

## Parameters and stated settings

- No user inputs; daily charts are recommended. Badge bull/bear boundary is 50%.

## Failure modes and caveats

- Trade volume and tick counts can differ in nature, so their ratio may not compare like quantities. Intraday totals can exceed EOD totals.
- Dataset length and missing observations affect cumulative results. Historical differences do not establish live-feed behavior or current vendor implementation.

## Missing information and implementation boundary

- The exact cumulative missing-value inclusion policy and badge normalization details are not supplied; feed identities and reporting policies require external investigation.

## Data requirements

Required inputs: historical minute-feed daily volume aggregation, historical end-of-day vendor volume feed, aligned daily session boundaries.

Repository input-class support: unavailable or unresolved. Requires distinct historical intraday and end-of-day vendor volume feeds; generic OHLCV cannot establish this comparison.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
The script is very simple and has no inputs.
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
the proportion of ​volume reported on the intraday feed over the ​​EOD ​volume
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
(% >= 50) or the bear color (% < 50)
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
data from the 1min intrabars of the historical intraday feed is aggregated over one day
```

### E5: purpose, mechanism, parameters, outputs_and_use, readiness

```text
The script only calculates on historical bars
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)
- [tv_tpseizhp_volume_x_ray_lucf](../../../strategy_research/tv_tpseizhp_volume_x_ray_lucf.md)

## Source

https://www.tradingview.com/script/tPsEizhp-Volume-X-ray-LucF/

Publication ID: tPsEizhp. Source SHA-256: 44305e92c0ae994b896b0b821f396bcfd9652d6963f1fbf642d36f608022945f. Raw-description SHA-256: 9ad9951b138dc04f8fe1e9a17f9e6ca4ac7d95bff95a28a21a946e3e0cae4672.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
