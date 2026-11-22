---

id: tv_profile_etm15sgp

name: "Moving Averages 3D"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare a family of moving averages through a three-dimensional-looking chart display rather than separate conventional lines."

registry_key: null

runner: null

evaluation: null

---

# Moving Averages 3D

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare a family of moving averages through a three-dimensional-looking chart display rather than separate conventional lines.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The description defines the ten average lengths and SMA/EMA choice, but not the price input or the projection and direction-color mapping that create the advertised three-dimensional indicator. Reconstructing those outputs would require new choices.

- The input price series is not identified.
- The three-dimensional projection and direction-color rules are not defined.

## How it works

- Use line fills to render ten moving averages. Their lengths form an arithmetic progression from a selected starting length and step.

## Outputs and intended use

- View the family's shape as an experimental visualization of price smoothing at different horizons. No crossover or trading rule is prescribed.

## Parameters and stated settings

- Choose SMA or EMA, starting length, step, direction colors and width. The example starting at 10 with step 5 yields lengths 10,15,20,25 and onward.

## Failure modes and caveats

- A perspective display can emphasize visual shape over exact price values. Correlated averages do not provide independent confirmations.

## Missing information and implementation boundary

- Price source, projection geometry, direction-color criteria and numerical defaults are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This is an experimental work to show 10 moving averages in 3D
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
You can set moving average type as Simple (SMA) or Exponential (EMA)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
For example; if "Starting Length" is 10 and "step" is 5 then the lengths are 10, 15, 20, 25...
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_etm15sgp_moving_averages_3d](../tv_etm15sgp_moving_averages_3d.md)

## Source

https://www.tradingview.com/script/EtM15SgP-Moving-Averages-3D/

Publication ID: EtM15SgP. Source SHA-256: 237ef6019f610b2a57991d503af8eba3ec066677d7c3c48e04e4269c3f30aa73. Raw-description SHA-256: 0936b94236260d7c6dc7835ba923b057996f4bb9ce46a70a48ba936e9c07b668.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
