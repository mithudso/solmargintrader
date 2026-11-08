---

id: tv_profile_hefekydl

name: "SMA Directional Matrix [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "SMA Directional Matrix shows whether simple moving averages across a chosen period range are rising or falling. It aims to reveal agreement between short-, medium- and long-horizon trend readings without overlaying many lines. Divergence between short and long averages can show a recent retracement against a broader direction. The source suggests balanced rising/falling counts during ranges, but does not define that as a formal regime threshold. The financial calculation is straightforward and parameterized; layout is the principal extra feature."

registry_key: null

runner: null

evaluation: null

---

# SMA Directional Matrix [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

SMA Directional Matrix shows whether simple moving averages across a chosen period range are rising or falling. It aims to reveal agreement between short-, medium- and long-horizon trend readings without overlaying many lines. Divergence between short and long averages can show a recent retracement against a broader direction. The source suggests balanced rising/falling counts during ranges, but does not define that as a formal regime threshold. The financial calculation is straightforward and parameterized; layout is the principal extra feature.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines a reproducible parameterized computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Compute SMAs for periods from user-selected Min through Max on Src.
- Associate each period with its current direction and place period/direction pairs in a configurable-column panel.

## Outputs and intended use

- Directional panel supports trend-cleanliness and retracement inspection.

## Parameters and stated settings

- Min,Max,Src and Number Of Columns are inputs; example period range25–50.

## Failure modes and caveats

- MA directions are strongly correlated and can lag turning points.
- Large period ranges can trigger String is too long or Loop is too long to execute errors.

## Missing information and implementation boundary

- Equal-value direction styling and numeric defaults are not stated; no trading rule is intended.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Source prices and SMA direction comparisons use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
direction of simple moving averages with periods in a user-selected range (Min, Max)
```

### E2: parameters

```text
periods ranging from 25 to 50
```

### E3: risks

```text
String is too long
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hefekydl_sma_directional_matrix_luxalgo](../../../strategy_research/tv_hefekydl_sma_directional_matrix_luxalgo.md)

## Source

https://www.tradingview.com/script/hefeKydL-SMA-Directional-Matrix-LuxAlgo/

Publication ID: hefeKydL. Source SHA-256: e33ac12fcca117ce1363cd8a87ec9f8341119e54765c96cb276dba5e60713e1e. Raw-description SHA-256: d4e30887a9d2d08cc86777e2b881df91033d83f935fcb0a9945f42293316279a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
