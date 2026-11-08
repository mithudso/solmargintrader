---

id: tv_profile_o0mu1wau

name: "CME Equity Futures Price Limits"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "This overlay draws CME-equity-futures-style price-limit references as a practical warning aid. It deliberately uses a simplified prior-session reference instead of reproducing the exchange’s stated reference calculation. The author admits omitted late-session nuances and advises checking the reference, so the output cannot be treated as an authoritative venue risk limit or a current specification of exchange rules."

registry_key: null

runner: null

evaluation: null

---

# CME Equity Futures Price Limits

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This overlay draws CME-equity-futures-style price-limit references as a practical warning aid. It deliberately uses a simplified prior-session reference instead of reproducing the exchange’s stated reference calculation. The author admits omitted late-session nuances and advises checking the reference, so the output cannot be treated as an authoritative venue risk limit or a current specification of exchange rules.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** For a caller-supplied manual reference, the stated percentage offsets define reproducible warning lines; official venue rules and automatic session reference are separate limitations.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Take the open of the last session’s candle as a proxy reference and apply the described percentage limit offsets.
- Allow a manual reference override for accuracy and an option to show only current/last-session lines.

## Outputs and intended use

- Use displayed levels as approximate context and verify against the venue’s actual reference/limits before relying on them.

## Parameters and stated settings

- Source describes out-of-session ±5% and downside levels -7%, -13%, -20%; these are historical source settings, not verified current exchange rules.

## Failure modes and caveats

- Reference approximation and omitted late-session nuances can misplace limits. The current/last-session-only option is stated to break in-session downside lines.

## Missing information and implementation boundary

- Session boundaries, contract coverage, current exchange rules, reference sampling and omitted nuances are unresolved.

## Data requirements

Required inputs: ohlcv, venue session calendar, verified current price-limit reference and rules.

Repository input-class support: unavailable or unresolved. The approximate chart calculation is OHLCV-based, but authoritative operational use requires external venue references and current rules.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, risks, readiness

```text
I took the open of the last session's candle because it's easier.
```

### E2: parameters, readiness

```text
Out of session breakers: +/-5%
Limit downs: -7%/-13%/-20%
```

### E3: risks, readiness

```text
This breaks the in session limit down lines.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_o0mu1wau_cme_equity_futures_price_limits](../tv_o0mu1wau_cme_equity_futures_price_limits.md)

## Source

https://www.tradingview.com/script/O0MU1wau-CME-Equity-Futures-Price-Limits/

Publication ID: O0MU1wau. Source SHA-256: cc2d0c092607de849a06dc902b5df02e73cb2d3fc808f279f15ab77b724ef86a. Raw-description SHA-256: 6afea9ccbe41f4327f5ed6ff46a93034fad4715b8ede571487b1d95d755319ee.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
