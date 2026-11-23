---

id: tv_profile_p9avc7vy

name: "TPO Market Profile [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Display a developing time-price-opportunity profile over a configurable session or calendar interval."

registry_key: null

runner: null

evaluation: null

---

# TPO Market Profile [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Display a developing time-price-opportunity profile over a configurable session or calendar interval.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: TPO time-slice definition, value-area percentage, tie expansion, initial-balance duration and tick-range defaults are absent.

- TPO time-slice definition, value-area percentage, tie expansion, initial-balance duration and tick-range defaults are absent.

## How it works

- Accumulate profile characters at price levels as time and high/low observations progress. Reset at selected timeframe boundaries or begin from a drag-and-drop start point. Add value area, POC and optional initial-balance range.

## Outputs and intended use

- Read letters/numbers as time/price occupancy, not traded-volume depth. Labels identify POC and value-area bounds near the interval start. Prior-session profile features were removed in the described version for load-time reasons.

## Parameters and stated settings

- Reset interval, start bar and manual/automatic tick spread are configurable. Release notes extend support to seconds-based charts; the text's older one-minute constraint is superseded within the same description.

## Failure modes and caveats

- Auto tick spacing may need manual adjustment across assets. Runtime and drawing limits can restrict retained history, and author reports of no errors are not independent validation.

## Missing information and implementation boundary

- TPO time-slice definition, value-area percentage, tie expansion, initial-balance duration and tick-range defaults are absent.

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
The TPO profile updates accordingly with changes in time / high and low prices. Letters are appended to the profile in real time.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The indicator hosts an option to auto calculate the tick spread between levels.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
UPDATE: The indicator can work on seconds-based charts.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Release Notes: Added value area + vah + val.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_profile](../tv_method_market_profile.md)
- [tv_method_opening_range](../tv_method_opening_range.md)
- [tv_p9avc7vy_tpo_market_profile_kioseff_trading](../tv_p9avc7vy_tpo_market_profile_kioseff_trading.md)

## Source

https://www.tradingview.com/script/P9aVc7vy-TPO-Market-Profile-Kioseff-Trading/

Publication ID: P9aVc7vy. Source SHA-256: b632a67fdf48582a6ab8200feab76dcbcb4e0d4a7c9deb12884417b69ffc8998. Raw-description SHA-256: 09ce9af4d8d61779d97df2cd5e8c864204ae9400c64c90fe86d7de2b87501c64.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
