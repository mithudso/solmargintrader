---

id: tv_profile_htj7v7sx

name: "Arbitrage Matrix [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare venue-reported prices or volumes for the same asset through a pairwise spread dashboard."

registry_key: null

runner: null

evaluation: null

---

# Arbitrage Matrix [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare venue-reported prices or volumes for the same asset through a pairwise spread dashboard.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for row-minus-column last-price or last-volume matrices when aligned mapped venue inputs are supplied; optional average modes and executable arbitrage validation remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For caller-supplied aligned observations of the same asset at enabled venues, calculate each last-value matrix cell as row venue value minus column venue value. This applies separately to last price or last volume; omit sources without data. Positive price cells mean the row is more expensive.
- Optional average-price/average-volume modes compare rolling averages; the default average length is 20, but exact averaging implementation is not printed. Automatic source selection uses crypto exchanges for crypto and forex brokers otherwise.

## Outputs and intended use

- A positive price cell means the row venue is more expensive than the column venue. Use the table to investigate discrepancies, not assume a displayed last-price spread is executable arbitrage profit.

## Parameters and stated settings

- All sources are enabled by default, automatic source type follows chart asset class, average length defaults twenty and background gradient defaults on. Data type, venue toggles, location, size and colors are adjustable.

## Failure modes and caveats

- Fees, bid/ask spreads, transfer delays, stale quotes, unit differences and execution limits can overwhelm a last-price difference. Volume across venues may use incompatible units.

## Missing information and implementation boundary

- Venue list/mapping, quote synchronization, averaging formula and any executable bid/ask/fee validation are missing.

## Data requirements

Required inputs: synchronized multi-venue price and volume series, venue-symbol mapping.

Repository input-class support: unavailable or unresolved. The external venue universe, mappings and aligned observations are not supplied; ordinary chart OHLCV cannot establish cross-venue spreads.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The default length for the average is 20.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
All are enabled by default.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
last price, last volume, average price, and average volume.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
sources without data will not be displayed.
```

### E5: mechanism, parameters, readiness

```text
The average BTCUSDT price over the last 20 days is $100 higher on Exchange A than on Exchange B.
```

### E6: mechanism, parameters, readiness

```text
If the value were -100, it would mean that the average price is $100 lower in Exchange A than in Exchange B.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_htj7v7sx_arbitrage_matrix_luxalgo](../tv_htj7v7sx_arbitrage_matrix_luxalgo.md)

## Source

https://www.tradingview.com/script/Htj7V7sx-Arbitrage-Matrix-LuxAlgo/

Publication ID: Htj7V7sx. Source SHA-256: 64a5b7531247adda0125827521ecca617c2d08afb53e0f7bcc6ad200e0a31b0d. Raw-description SHA-256: be81a74f50dbf550d2e7f42f5af7b487dff4b84ce47d02fd1651875445a2c845.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
