---

id: tv_profile_wfcbsk6s

name: "Market Cap Landscape 3D"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Market Cap Landscape 3D ranks user-selected crypto market capitalizations and places them on a decorative mountain scene. Its financial content is the capitalization leaderboard and rank hierarchy, so it remains in scope despite its artistic presentation. The mountain mesh itself is procedural scenery, not a literal market-cap surface or historical price path. The largest selected asset occupies the summit and the others are positioned by rank. Optional developer instructions show how another metric could replace capitalization, but those modifications are examples rather than existing alternative modes."

registry_key: null

runner: null

evaluation: null

---

# Market Cap Landscape 3D

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Cap Landscape 3D ranks user-selected crypto market capitalizations and places them on a decorative mountain scene. Its financial content is the capitalization leaderboard and rank hierarchy, so it remains in scope despite its artistic presentation. The mountain mesh itself is procedural scenery, not a literal market-cap surface or historical price path. The largest selected asset occupies the summit and the others are positioned by rank. Optional developer instructions show how another metric could replace capitalization, but those modifications are examples rather than existing alternative modes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines a reproducible parameterized computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Fetch CRYPTOCAP symbol closes as capitalization values and sort descending.
- Place the leading asset at the summit and distribute others by rank elevation; show exact values on a leaderboard.

## Outputs and intended use

- 3D labels, summit flag and ranked capitalization list support cross-asset size comparison.

## Parameters and stated settings

- Up to forty unique symbols; comma-separated list handles duplicates/case.
- Camera yaw/pitch/scales, mesh resolution, fills, flags, labels and thirteen palettes are configurable.
- Developer example substitutes daily RSI14; it is an illustrative code modification.

## Failure modes and caveats

- Scene elevation represents rank and procedural geometry, not proportional capitalization.
- Missing CRYPTOCAP symbols error, and current selected names do not constitute a historical universe.

## Missing information and implementation boundary

- Exact missing-data/tie treatment and mesh placement equations are absent; financial ranking itself is straightforward.

## Data requirements

Required inputs: CRYPTOCAP capitalization series, user-selected crypto universe.

Repository input-class support: unavailable or unresolved. External capitalization series and a concrete user list are required; coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
sorts them in descending order
```

### E2: parameters

```text
up to 40 unique symbols.
```

### E3: parameters

```text
13 stunning, pre-designed color themes
```

### E4: parameters

```text
Ranking by RSI (14) on the Daily timeframe.
```

### E5: required_data

```text
exclusively uses TradingView's `CRYPTOCAP` data source.
```

## Source

https://www.tradingview.com/script/WFCBSK6s-Market-Cap-Landscape-3D/

Publication ID: WFCBSK6s. Source SHA-256: e157f662be578b9332f946471710ac2bb55d645b8c7e084f91d6887ac40e6725. Raw-description SHA-256: 495c4ef118646d7a53ac1ab6ac50498f97c1e0390394df81bf9db3b4dcf3b65f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
