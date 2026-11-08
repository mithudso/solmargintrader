---

id: tv_profile_zr3wnj4k

name: "Trading Holidays and Expiry Calendar"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Trading Holidays and Expiry Calendar shows a forward calendar of market activity classifications. It aims to help users and script developers distinguish trading sessions, closures, weekends and expiry events before those dates arrive. This is a financial planning tool even though it generates no price signal. The source describes the display and the division between user-provided expiry information and automatically derived days, but does not disclose which exchange calendar or holiday rules it uses."

registry_key: null

runner: null

evaluation: null

---

# Trading Holidays and Expiry Calendar

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trading Holidays and Expiry Calendar shows a forward calendar of market activity classifications. It aims to help users and script developers distinguish trading sessions, closures, weekends and expiry events before those dates arrive. This is a financial planning tool even though it generates no price signal. The source describes the display and the division between user-provided expiry information and automatically derived days, but does not disclose which exchange calendar or holiday rules it uses.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core rules remain unresolved.

- Holiday derivation and expiry rule/input contracts are absent.

## How it works

- Render the current and following months as a calendar.
- Mark expiry days from user input and derive the other day classifications automatically.

## Outputs and intended use

- Inspect upcoming closures and expiries as scheduling context.
- Developers may reuse calendar functions in financial indicators or strategies, subject to validating their market calendar.

## Parameters and stated settings

- The display spans the current month plus the next two months, for three months total.
- A simple input controls expiry marking, but its precise format/default is absent.

## Failure modes and caveats

- Exchange-specific holidays and exceptional closures cannot be safely inferred from weekends alone.
- Expiry conventions can change and may be adjusted around holidays.

## Missing information and implementation boundary

- Supported exchange, timezone, holiday dataset/algorithm, expiry input schema and adjustment rules are missing.

## Data requirements

Required inputs: exchange holiday calendar, user expiry rules.

Repository input-class support: unavailable or unresolved. Calendar or detailed live/lower-timeframe data are not available from ordinary chart bars.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
current and next 2 months.
```

### E2: parameters

```text
Calendar view of 3 months Trading days
```

### E3: mechanism

```text
‘Expiry Days’ are marked based on User input and rest of the days are derived and marked automatically.
```

## Source

https://www.tradingview.com/script/zR3wnj4k-Trading-Holidays-and-Expiry-Calendar/

Publication ID: zR3wnj4k. Source SHA-256: 3a94371db7c6a72512015b58f51ab3ae6a532cb1a11860cc3abc891f6737c4a9. Raw-description SHA-256: 2344f6e3c7f1cf43636510b9a6488ca4fee939e668e477a10a240923f6b53a7c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
