---

id: tv_profile_kzjqxdgq

name: "COT Net Non-Commercials vs Commercials (Updated MTF Non-Repaint)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "This COT overlay compares commercial and noncommercial net positioning in one display. It aims to show whether producer/hedger-style and speculator-style groups are net positive or negative and how dense or shallow those positions appear. The author’s non-repainting wording is a claim about the script, not a verified guarantee about point-in-time report availability or data revisions."

registry_key: null

runner: null

evaluation: null

---

# COT Net Non-Commercials vs Commercials (Updated MTF Non-Repaint)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This COT overlay compares commercial and noncommercial net positioning in one display. It aims to show whether producer/hedger-style and speculator-style groups are net positive or negative and how dense or shallow those positions appear. The author’s non-repainting wording is a claim about the script, not a verified guarantee about point-in-time report availability or data revisions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Supplied-net-position comparison is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve CFTC COT series through the source-stated Quandl pathway and display commercial/noncommercial net values together.
- Plot supplied noncommercial net green and commercial net red on a common signed axis;negative stays below zero. Net construction,feed mapping/release timing,MTF/nonrepaint excluded.

## Outputs and intended use

- Green denotes noncommercial/speculator positions and red commercial/producer positions; compare their signs and historical extremes as descriptive context.
- Usable scope: Supplied-net-position comparison. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Multi-timeframe use is claimed; no CFTC mapping, net formula, source codes, default window or extreme thresholds are disclosed.

## Failure modes and caveats

- Analytical: report publication lag, revisions and broad category definitions limit contemporaneous sentiment inference; feed availability may have changed since publication.

## Missing information and implementation boundary

- Exact net calculation, contract/category series, release-time alignment, scaling and MTF confirmation implementation are absent.

## Data requirements

Required inputs: CFTC commercial/noncommercial positioning histories, release timestamps and symbol mapping.

Repository input-class support: unavailable or unresolved. COT reports are external data and require a market mapping and publication-time contract.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: outputs_and_use, readiness

```text
Green - Non Commercials - Speculators
Red    - Commercials - Producers
```

### E2: mechanism, readiness

```text
Data  pulled through Quandl.
```

### E3: risks, readiness

```text
multi time-frame and non-repaint script.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Green - Non Commercials - Speculators
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
Red    - Commercials - Producers
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_kzjqxdgq_cot_net_non_commercials_vs_commercials_updated_mtf_non_repaint](../tv_kzjqxdgq_cot_net_non_commercials_vs_commercials_updated_mtf_non_repaint.md)

## Source

https://www.tradingview.com/script/KZJQxDgq-COT-Net-Non-Commercials-vs-Commercials-Updated-MTF-Non-Repaint/

Publication ID: KZJQxDgq. Source SHA-256: 6ca1036c140769019a67b22ee1eb3f6f92faf3b450fc1cd41c7daadc4607f394. Raw-description SHA-256: 66172f6091b5ee83ae12b476514d3c64b33a3551f0553f7d3a932292c8026b34.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
