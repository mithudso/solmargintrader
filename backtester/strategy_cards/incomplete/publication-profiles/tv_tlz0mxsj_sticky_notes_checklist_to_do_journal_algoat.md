---

id: tv_profile_tlz0mxsj

name: "Sticky Notes, Checklist, To-do, Journal [algoat]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Sticky Notes, Checklist, To-do, Journal puts a trader’s own notes and plans directly on the chart. Its financial purpose is workflow support rather than price analysis: the user can record market insights, trade plans, tasks and deadlines near the chart being monitored. Generic advice about confirming indicators in the latter description does not imply this note tool computes technical signals. The useful artifact is a visible user-maintained checklist/journal. No automatic trading inference should be drawn from overdue colors or checked tasks."

registry_key: null

runner: null

evaluation: null

---

# Sticky Notes, Checklist, To-do, Journal [algoat]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Sticky Notes, Checklist, To-do, Journal puts a trader’s own notes and plans directly on the chart. Its financial purpose is workflow support rather than price analysis: the user can record market insights, trade plans, tasks and deadlines near the chart being monitored. Generic advice about confirming indicators in the latter description does not imply this note tool computes technical signals. The useful artifact is a visible user-maintained checklist/journal. No automatic trading inference should be drawn from overdue colors or checked tasks.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The input/storage contract and overdue-date comparison are not specified.

## How it works

- Display user-entered notes/journal entries and task checkmarks.
- Associate due dates with tasks and mark overdue items visually.

## Outputs and intended use

- Chart note board supports trade preparation, journaling and task reminders.

## Parameters and stated settings

- Note size and position are configurable; source gives no field limits/defaults.

## Failure modes and caveats

- Manual notes can become stale or be mistaken for current validated analysis.
- A checklist mark does not verify a trade condition or execution.

## Missing information and implementation boundary

- Input/storage format, due-date timezone/comparison, persistence, capacity and symbol-specific behavior are absent.

## Data requirements

Required inputs: user-entered trading notes/tasks/dates.

Repository input-class support: unavailable or unresolved. The required content is user-authored and not supplied by market OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, outputs_and_use

```text
market insights, trade plans
```

### E2: mechanism, readiness

```text
Red alert for overdue tasks
```

### E3: parameters

```text
Choose the size and position of your notes
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_value_investing](../tv_method_value_investing.md)

## Source

https://www.tradingview.com/script/Tlz0MxsJ-Sticky-Notes-Checklist-To-do-Journal-algoat/

Publication ID: Tlz0MxsJ. Source SHA-256: e0e8751724168f64c3d85f8001bb9a48d3452fa98aaa407bc2b7f33ae7df5abe. Raw-description SHA-256: ce1423fe3c9b9ddace569439d8482a233c22d137a0aeb598decf8013828c218e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
