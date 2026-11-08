---

id: tv_profile_4n9sh3lz

name: "Funamental and financials"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Place a company's quarterly financial condition beside its market chart so trends in debt, cash and earnings can be reviewed together."

registry_key: null

runner: null

evaluation: null

---

# Funamental and financials

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Place a company's quarterly financial condition beside its market chart so trends in debt, cash and earnings can be reviewed together.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: Exact financial identifiers, valuation denominators, publication-date alignment and missing-report behavior are unspecified. No financial-health scoring or trading rule is defined.

- Exact financial identifiers, valuation denominators, publication-date alignment and missing-report behavior are unspecified. No financial-health scoring or trading rule is defined.

## How it works

- Request financial-function data and present it with text boxes instead of numerous plotted lines. Scale the values per share, relative to market valuation or as aggregate reported amounts.

## Outputs and intended use

- Use per-share information on a daily chart for a compact health overview, percentage-of-market-value information to compare with share price, and aggregate mode to check quarterly reports.

## Parameters and stated settings

- Normal mode is per share. Aggregate figures are divided by 1,000,000 for readability. The description recommends a daily chart but does not list individual financial fields or default dates.

## Failure modes and caveats

- The author reports slow loading, overlapping text boxes and incomplete quarterly text placement. Fundamental history may also depend on reporting availability and revisions.

## Missing information and implementation boundary

- Exact financial identifiers, valuation denominators, publication-date alignment and missing-report behavior are unspecified. No financial-health scoring or trading rule is defined.

## Data requirements

Required inputs: company quarterly financial data, share count and share price for scaling.

Repository input-class support: unavailable or unresolved. Financial statements and share-count/valuation inputs are external to OHLCV and are neither supplied nor verified by this saved description.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The intent is to create an indicator that instantly show the financial health of a company, and the trends in debt, cash and earnings
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Normal settings displays all information on a per share basis, and should be viewed on a Daily chart
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
And actual to show the full numbers for verification with quarterly reporting and debuggging (actual is divided by 1.000.000 to keep numbers readable)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_4n9sh3lz_funamental_and_financials](../tv_4n9sh3lz_funamental_and_financials.md)

## Source

https://www.tradingview.com/script/4n9Sh3Lz-Funamental-and-financials/

Publication ID: 4n9Sh3Lz. Source SHA-256: 6875ef995e980d250153db33b307fc111c0d7a9f5e86e19ff191066811c0beb2. Raw-description SHA-256: 02ad9e710d3344c240bd4dd4acb1a4c0feac1a30d503f3d7ef2249d008ba6193.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
