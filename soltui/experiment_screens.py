"""Presentation for the optimization workbench; every operation uses the registry."""
from __future__ import annotations

from collections.abc import Callable
import math
import time
from typing import Any, ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)


def _number(value: Any) -> str:
    if value is None:
        return "unknown"
    return f"{value:,.6g}" if isinstance(value, (float, int)) else str(value)


def _config(values: dict[str, Any]) -> str:
    return "  ".join(f"{key}={_number(value)}" for key, value in values.items())


class ExperimentScreen(ModalScreen[None]):
    """Typed search setup, durable run controls and inspectable evidence.

    Commands execute on worker threads. Polls are bounded and non-overlapping;
    dismissal stops the timer and drops late callbacks. Explicitly started
    optimization subprocesses remain independent of the screen's lifetime.
    """
    DEFAULT_CSS = """
    ExperimentScreen { align: center middle; }
    #exp-dialog { width: 98%; height: 96%; border: thick $accent; background: $surface; padding: 0 1; }
    #exp-title, #exp-status { height: auto; max-height: 5; }
    #exp-status { color: $accent; }
    #exp-tabs { height: 1fr; }
    ExperimentScreen .exp-row { height: 3; }
    ExperimentScreen .exp-row Input { width: 1fr; }
    ExperimentScreen .exp-row Select { width: 1fr; }
    ExperimentScreen .exp-row Label { width: 16; padding: 1 0; }
    ExperimentScreen .exp-row Button { min-width: 12; }
    ExperimentScreen DataTable { height: 12; }
    ExperimentScreen .exp-detail { height: auto; min-height: 3; }
    #exp-run-table { height: 10; }
    #exp-candidate-table { height: 12; }
    #exp-bottom { height: 3; }
    """
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("escape", "close", "Close")]

    def __init__(self, bot: str, call: Callable[[str, dict[str, Any]], dict[str, Any]],
                 coins: list[str] | None = None) -> None:
        super().__init__()
        self.bot, self.call, self.coins = bot, call, coins or []
        self.space: dict[str, dict[str, Any]] = {}
        self.baseline: dict[str, Any] = {}
        self.domains: dict[str, Any] = {}
        self.run_id = ""
        self.run: dict[str, Any] = {}
        self.runs: list[dict[str, Any]] = []
        self.candidate_rows: list[dict[str, Any]] = []
        self.selected_candidate = ""
        self.preview: dict[str, Any] | None = None
        self._preview_request: dict[str, Any] | None = None
        self._timer = None
        self._polling = False
        self._workbench_closed = False

    def compose(self) -> ComposeResult:
        with Vertical(id="exp-dialog"):
            yield Static(Text(f"Optimization workbench · {self.bot} · simulation / imported evidence"), id="exp-title")
            yield Static("Loading saved experiments…", id="exp-status", markup=False)
            with TabbedContent(id="exp-tabs", initial="exp-search"):
                with TabPane("Search setup", id="exp-search"), VerticalScroll():
                    yield Static("Choose a parameter and its type, then Add/update. Unspecified settings stay fixed at the baseline. "
                                 "Preview validates configurations and actual cached-data workload before launch.", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Label("Parameter")
                        yield Select([], id="exp-param")
                        yield Select([("Fixed", "fixed"), ("Explicit values", "enum"),
                                      ("Linear range + step", "linear"), ("Log range + count", "log")],
                                     value="fixed", allow_blank=False, id="exp-kind")
                    with Horizontal(classes="exp-row"):
                        yield Label("Value(s)")
                        yield Input(placeholder='Fixed value or comma-separated enum, e.g. 3,5,9 or geom,arith', id="exp-values")
                    yield Static("", id="exp-units", classes="exp-detail", markup=False)
                    for label, name, default in (("Start", "start", "-10"), ("Stop (inclusive)", "stop", "10"),
                                                 ("Step / count", "step", "10")):
                        with Horizontal(classes="exp-row"):
                            yield Label(label)
                            yield Input(placeholder=label.lower(), id=f"exp-{name}")
                            yield Input(value=default, placeholder="% of baseline", id=f"exp-{name}-pct")
                            yield Button("Apply %", id=f"exp-{name}-adjust")
                    with Horizontal(classes="exp-row"):
                        yield Button("Add/update", id="exp-add")
                        yield Button("Remove", id="exp-remove")
                    yield DataTable(id="exp-space-table", cursor_type="row")
                    yield Static("", id="exp-baseline", classes="exp-detail", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Label("Coins")
                        yield Input(value=",".join(self.coins), placeholder="empty = every cached coin; ignored for triangle", id="exp-coins")
                        yield Button("Refresh live price", id="exp-price-refresh")
                    yield Static("Live price: not requested. Prices do not set parameter values.", id="exp-live-price",
                                 classes="exp-detail", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Label("Windows / days")
                        yield Input(value="6", placeholder="windows", id="exp-windows")
                        yield Input(value="30", placeholder="days per window", id="exp-days")
                        yield Input(value="97", placeholder="max configurations", id="exp-max-candidates")
                        yield Input(value="20000", placeholder="max evaluations", id="exp-max-evaluations")
                    with Horizontal(classes="exp-row"):
                        yield Button("Preview workload", variant="primary", id="exp-preview")
                        yield Button("Create + explore", variant="success", id="exp-create", disabled=True)
                    yield Static("No preview yet. Final holdout values remain sealed during exploration.", id="exp-preview-summary",
                                 classes="exp-detail", markup=False)
                    yield DataTable(id="exp-preview-table", cursor_type="row")
                with TabPane("Experiments", id="exp-explorer"), VerticalScroll():
                    with Horizontal(classes="exp-row"):
                        yield Button("Refresh runs", id="exp-refresh")
                        yield Input(placeholder="Find run by ID or source", id="exp-run-filter")
                    yield DataTable(id="exp-run-table", cursor_type="row")
                    with Horizontal(classes="exp-row"):
                        yield Button("Resume explore", id="exp-resume")
                        yield Button("Pause", id="exp-pause")
                        yield Button("Cancel", id="exp-cancel", variant="error")
                        yield Button("Final validate", id="exp-final", variant="warning")
                    yield Checkbox("Adopt only if gate passes", value=False, id="exp-adopt")
                    yield Static("Select a saved run. Closing this window leaves its explicit worker running. "
                                 "Pause/cancel take effect after the current cell commits.", id="exp-run-detail",
                                 classes="exp-detail", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Label("Sort candidates")
                        yield Select([("Return median ↓", "total_return"), ("Drawdown loss ↑", "max_drawdown"),
                                      ("Trades ↓", "trades"), ("Triangle P&L ↓", "pnl_usd"), ("Candidate ID", "candidate_id")],
                                     value="total_return", allow_blank=False, id="exp-sort")
                    yield DataTable(id="exp-candidate-table", cursor_type="row")
                    yield Static("Select a candidate for its full configuration and coin/window evidence.",
                                 id="exp-candidate-detail", classes="exp-detail", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Input(placeholder="Coin filter (empty = all)", id="exp-cell-coin")
                        yield Select([("Train + validation", ""), ("Train", "train"), ("Validation", "validation"),
                                      ("Final holdout (after finalization)", "holdout")],
                                     value="", allow_blank=False, id="exp-cell-split")
                        yield Select([("All statuses", ""), ("Completed", "completed"), ("Failed", "failed")],
                                     value="", allow_blank=False, id="exp-cell-status")
                        yield Button("Filter evidence", id="exp-filter-cells")
                    yield DataTable(id="exp-cell-table", cursor_type="row")
                    yield Static("", id="exp-cell-detail", classes="exp-detail", markup=False)
                with TabPane("Stability map", id="exp-stability"), VerticalScroll():
                    yield Static("Observed train/validation values only. Each slice fixes every other setting. "
                                 "A dot marks an unobserved point; no interpolation.", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Label("Parameter axes")
                        yield Select([], id="exp-map-x")
                        yield Select([], id="exp-map-y")
                        yield Select([("Return", "total_return"), ("Drawdown loss", "max_drawdown"), ("Trades", "trades"), ("Triangle P&L (USD)", "pnl_usd")],
                                     value="total_return", allow_blank=False, id="exp-map-metric")
                    with Horizontal(classes="exp-row"):
                        yield Input(placeholder="Coin (empty = all)", id="exp-map-coin")
                        yield Select([("Train + validation", ""), ("Train", "train"), ("Validation", "validation")],
                                     value="", allow_blank=False, id="exp-map-split")
                        yield Button("Build observed map", variant="primary", id="exp-heatmap")
                    yield Select([], prompt="Conditioned configuration slice", id="exp-map-group")
                    yield Static("Select a native or imported experiment first.", id="exp-map-summary", classes="exp-detail", markup=False)
                    yield DataTable(id="exp-map-table", cursor_type="row")
                    yield DataTable(id="exp-map-points", cursor_type="row")
                with TabPane("TradingView import / compare", id="exp-import-tab"), VerticalScroll():
                    yield Static("Import a result CSV, then compare explicit provenance. Imported evidence cannot adopt native settings. "
                                 "Missing units, dates, costs or fill timing remain unknown and prevent a comparable verdict.", markup=False)
                    with Horizontal(classes="exp-row"):
                        yield Label("CSV file")
                        yield Input(placeholder="Absolute local CSV path", id="exp-import-path")
                    for label, ids in (("Identity", ("coin", "interval", "currency", "script")),
                                       ("Provenance", ("strategy", "data_source", "label")),
                                       ("Dates (UTC)", ("start", "end")),
                                       ("Cost / timing", ("fee_bps", "slippage_bps", "borrow_bps_per_day", "fill_delay"))):
                        with Horizontal(classes="exp-row"):
                            yield Label(label)
                            for name in ids:
                                yield Input(placeholder=name, id=f"exp-meta-{name}")
                    with Horizontal(classes="exp-row"):
                        yield Label("Return / DD units")
                        for name in ("return_unit", "drawdown_unit"):
                            yield Select([("Unknown", ""), ("Fraction", "fraction"), ("Percent", "percent"),
                                          ("Currency P&L", "currency")], value="", allow_blank=False, id=f"exp-meta-{name}")
                        yield Button("Import CSV", variant="primary", id="exp-import")
                    with Horizontal(classes="exp-row"):
                        yield Label("Compare IDs")
                        yield Input(placeholder="left experiment ID (defaults selected run)", id="exp-compare-left")
                        yield Input(placeholder="right experiment ID", id="exp-compare-right")
                        yield Button("Compare", id="exp-compare")
                    yield Static("", id="exp-compare-summary", classes="exp-detail", markup=False)
                    yield DataTable(id="exp-compare-table", cursor_type="row")
                    yield Static("", id="exp-compare-detail", classes="exp-detail", markup=False)
            with Horizontal(id="exp-bottom"):
                yield Button("Close", id="exp-close")

    def on_mount(self) -> None:
        for wid, cols in {
            "exp-space-table": ("Parameter", "Mode", "Values / range"),
            "exp-preview-table": ("Candidate", "Full configuration"),
            "exp-run-table": ("ID", "Source", "Bot", "Status", "Updated"),
            "exp-candidate-table": ("Candidate", "Completed", "Failed", "Return", "DD loss (fraction)", "Trades", "Return spread"),
            "exp-cell-table": ("Candidate", "Coin", "Split", "Start", "End", "Status", "Return", "Drawdown (raw)", "Trades", "Error"),
            "exp-map-points": ("x", "y", "Median", "Observations", "Std dev", "Min", "Max", "Failed"),
            "exp-compare-table": ("Provenance", "Left", "Right", "Match"),
        }.items():
            self.query_one(f"#{wid}", DataTable).add_columns(*cols)
        self._command("experiments.schema", {"bot": self.bot}, self._schema)
        self.refresh_runs()
        if len(self.coins) == 1:
            self.refresh_live_price()
        self._timer = self.set_interval(1.0, self._poll)

    def _command(self, name: str, params: dict[str, Any], callback: Callable[[Any], None] | None = None,
                 *, quiet: bool = False) -> None:
        if not quiet:
            self.query_one("#exp-status", Static).update(Text(f"{name}…"))

        def worker() -> None:
            try:
                env = self.call(name, params)
            except Exception as exc:  # noqa: BLE001 - registry boundary keeps unexpected errors visible in the modal
                env = {"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}}
            try:
                self.app.call_from_thread(self._received, name, env, callback, quiet)
            except RuntimeError:
                pass  # Application already shut down; no widget callbacks remain.
        self.run_worker(worker, thread=True, exit_on_error=False, group="experiment-commands")

    def _received(self, name: str, env: dict[str, Any], callback: Callable | None, quiet: bool) -> None:
        if self._workbench_closed or not self.is_attached:
            return
        if not env.get("ok"):
            self._polling = False
            if name == "prices.status":
                self.query_one("#exp-live-price", Static).update(Text("Live price unavailable: recorder status failed."))
            self.query_one("#exp-status", Static).update(Text(f"{name}: {env.get('error', {}).get('message', 'unknown error')}"))
            return
        if not quiet:
            self.query_one("#exp-status", Static).update(Text(f"{name}: done"))
        if callback:
            callback(env.get("result"))

    def _schema(self, result: dict[str, Any]) -> None:
        self.baseline, self.domains = result["baseline"], result["domains"]
        choices = [(f"{name} ({domain[0]})", name) for name, domain in self.domains.items()]
        self.query_one("#exp-param", Select).set_options(choices)
        names = list(self.domains)
        if names:
            self.query_one("#exp-param", Select).value = names[0]
        self._axes(list(self.baseline))
        self.query_one("#exp-baseline", Static).update(Text("Baseline: " + _config(self.baseline)))

    @on(Select.Changed, "#exp-param")
    def _parameter_changed(self, event: Select.Changed) -> None:
        name = self._selected("exp-param")
        if name not in self.domains or name not in self.baseline:
            return
        domain, baseline = self.domains[name], self.baseline[name]
        self.query_one("#exp-values", Input).value = str(baseline)
        choice = domain[0] == "choice"
        if choice:
            self.query_one("#exp-units", Static).update(Text("Choice values: " + ", ".join(map(str, domain[1])) +
                                                               ". Use Fixed or Explicit values; ranges do not apply."))
            for part in ("start", "stop", "step"):
                self.query_one(f"#exp-{part}", Input).value = ""
        else:
            lo, hi = float(domain[1]), float(domain[2])
            base = float(baseline)
            span = abs(base) * .1 or (hi - lo) * .1
            integer = domain[0] == "int"
            low, high = max(lo, base - span), min(hi, base + span)
            step = max(1., round(span)) if integer else span
            if integer:
                low, high = int(round(low)), int(round(high))
            for part, val in (("start", low), ("stop", high), ("step", step)):
                self.query_one(f"#exp-{part}", Input).value = str(int(val) if integer else float(val))
            unit = ("percent points" if name.endswith("_pct") else "basis points" if name.endswith("_bps") else
                    "seconds" if name.endswith("_s") else "bars" if name.endswith("_bars") else
                    "whole number" if integer else "parameter units")
            self.query_one("#exp-units", Static).update(Text(
                f"{name}: {unit}; baseline {baseline}; allowed {domain[1]} to {domain[2]}. "
                "Start/stop are actual values. Adjustments use the baseline; step % is its magnitude. "
                "Whole numbers are rounded; zero baseline cannot use % adjustments."))
        for part in ("start", "stop", "step"):
            self.query_one(f"#exp-{part}", Input).disabled = choice
            disabled = choice or (part == "step" and self._selected("exp-kind") == "log")
            self.query_one(f"#exp-{part}-pct", Input).disabled = disabled
            self.query_one(f"#exp-{part}-adjust", Button).disabled = disabled
        if not choice and self._selected("exp-kind") == "log":
            self.query_one("#exp-step", Input).value = "5"

    @on(Select.Changed, "#exp-kind")
    def _kind_changed(self, event: Select.Changed) -> None:
        name = self._selected("exp-param")
        choice = self.domains.get(name, ("choice",))[0] == "choice"
        logarithmic = self._selected("exp-kind") == "log"
        self.query_one("#exp-step-pct", Input).disabled = choice or logarithmic
        self.query_one("#exp-step-adjust", Button).disabled = choice or logarithmic
        self.query_one("#exp-step", Input).placeholder = "number of values (whole number)" if logarithmic else "step in parameter units"
        if logarithmic and not choice:
            self.query_one("#exp-step", Input).value = "5"

    @on(Button.Pressed, "#exp-start-adjust, #exp-stop-adjust, #exp-step-adjust")
    def adjust_parameter(self, event: Button.Pressed) -> None:
        part = str(event.button.id).removeprefix("exp-").removesuffix("-adjust")
        name = self._selected("exp-param")
        domain = self.domains.get(name)
        try:
            if not domain or domain[0] == "choice":
                raise ValueError("Choose a numeric parameter.")
            if part == "step" and self._selected("exp-kind") == "log":
                raise ValueError("Logarithmic count is a whole number, not a percentage.")
            base = float(self.baseline[name])
            percent = float(self._input(f"exp-{part}-pct"))
            if not math.isfinite(percent) or not math.isfinite(base) or base == 0:
                raise ValueError("Use a finite percentage and a nonzero baseline.")
            value = abs(base) * abs(percent) / 100 if part == "step" else base * (1 + percent / 100)
            if domain[0] == "int":
                value = int(round(value))
            if not math.isfinite(value) or (part == "step" and value <= 0):
                raise ValueError("The adjusted step must be positive.")
            if part != "step" and not domain[1] <= value <= domain[2]:
                raise ValueError(f"Adjusted value must be within {domain[1]} to {domain[2]}.")
            self.query_one(f"#exp-{part}", Input).value = str(value)
        except (ValueError, OverflowError) as exc:
            self.query_one("#exp-status", Static).update(Text(str(exc)))

    def _axes(self, names: list[str]) -> None:
        choices = [(name, name) for name in names]
        for wid in ("exp-map-x", "exp-map-y"):
            self.query_one(f"#{wid}", Select).set_options(choices)
        if names:
            self.query_one("#exp-map-x", Select).value = names[0]
            self.query_one("#exp-map-y", Select).value = names[min(1, len(names) - 1)]

    def _input(self, wid: str) -> str:
        return self.query_one(f"#{wid}", Input).value.strip()

    def _selected(self, wid: str) -> str:
        value = self.query_one(f"#{wid}", Select).value
        return "" if value is Select.BLANK else str(value)

    def _invalidate(self) -> None:
        self.preview = None
        self._preview_request = None
        self.query_one("#exp-create", Button).disabled = True

    @on(Input.Changed)
    def _input_changed(self, event: Input.Changed) -> None:
        if event.input.id in {"exp-coins", "exp-windows", "exp-days", "exp-max-candidates", "exp-max-evaluations"}:
            self._invalidate()
        if event.input.id == "exp-coins":
            self.query_one("#exp-live-price", Static).update(Text("Live price: refresh after changing the coin."))
        if event.input.id == "exp-run-filter":
            self._render_runs()

    @on(Button.Pressed, "#exp-price-refresh")
    def refresh_live_price(self) -> None:
        coins = [part.strip().upper() for part in self._input("exp-coins").split(",") if part.strip()]
        if len(coins) != 1:
            self.query_one("#exp-live-price", Static).update(Text("Live price unavailable: choose exactly one coin."))
            return
        coin = coins[0]
        self.query_one("#exp-live-price", Static).update(Text(f"Checking {coin} live price…"))
        self._command("prices.status", {}, lambda result: self._show_live_price(coin, result), quiet=True)

    def _show_live_price(self, coin: str, result: Any) -> None:
        if self._input("exp-coins").strip().upper() != coin:
            return
        text = f"Live price unavailable for {coin}: no fresh verified recorder quote."
        try:
            quote = result["prices"][coin + "-USD"]
            bid, ask, age = float(quote["bid"]), float(quote["ask"]), float(quote["quote_age_s"])
            snapshot_age = float(result["snapshot_age_s"])
            if (result["live"] is True and all(math.isfinite(x) for x in (bid, ask, age, snapshot_age)) and
                    0 <= age < 10 and 0 <= snapshot_age < 10 and 0 < bid <= ask):
                observed = time.strftime("%H:%M:%S UTC", time.gmtime(time.time() - age))
                text = f"{coin}-USD recorder midpoint: ${(bid + ask) / 2:,.6g} (quote {observed}); parameter values are separate."
        except (TypeError, ValueError, KeyError, OverflowError):
            pass
        self.query_one("#exp-live-price", Static).update(Text(text))

    @on(Button.Pressed, "#exp-add")
    def add_parameter(self) -> None:
        name = self._selected("exp-param")
        if not name:
            return
        domain = self.domains[name]
        def value(text: str) -> Any:
            if domain[0] == "choice":
                return text.strip().strip('"')
            return int(text) if domain[0] == "int" else float(text)
        kind = self._selected("exp-kind")
        try:
            if domain[0] == "choice" and kind not in ("fixed", "enum"):
                raise ValueError("choice parameters require fixed or explicit values")
            if kind == "fixed":
                spec = {"kind": "fixed", "value": value(self._input("exp-values"))}
            elif kind == "enum":
                spec = {"kind": "enum", "values": [value(v) for v in self._input("exp-values").split(",")]}
            else:
                spec = {"kind": "range", "start": value(self._input("exp-start")),
                        "stop": value(self._input("exp-stop")), "scale": "log" if kind == "log" else "linear"}
                spec["count" if kind == "log" else "step"] = (int(self._input("exp-step")) if kind == "log"
                                                             else value(self._input("exp-step")))
            self.space[name] = spec
            self._invalidate()
            self._render_space()
        except ValueError:
            self.query_one("#exp-status", Static).update(Text("Enter values matching the selected parameter type."))

    @on(Button.Pressed, "#exp-remove")
    def remove_parameter(self) -> None:
        self.space.pop(self._selected("exp-param"), None)
        self._invalidate()
        self._render_space()

    def _render_space(self) -> None:
        table = self.query_one("#exp-space-table", DataTable)
        table.clear()
        for name, spec in self.space.items():
            table.add_row(name, str(spec["kind"]), _config({k: v for k, v in spec.items() if k != "kind"}))

    def _search_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"bot": self.bot, "space": self.space.copy(),
            "windows": int(self._input("exp-windows")), "window_days": int(self._input("exp-days")),
            "max_candidates": int(self._input("exp-max-candidates")), "max_evaluations": int(self._input("exp-max-evaluations"))}
        coins = [c.strip().upper() for c in self._input("exp-coins").split(",") if c.strip()]
        if coins:
            params["coins"] = coins
        return params

    @on(Button.Pressed, "#exp-preview")
    def preview_search(self) -> None:
        try:
            params = self._search_params()
        except ValueError:
            self.query_one("#exp-status", Static).update(Text("Windows, days and budgets must be integers."))
            return
        self._invalidate()
        self._command("experiments.preview", params, lambda result: self._previewed(result, params))

    def _previewed(self, result: dict[str, Any], params: dict[str, Any]) -> None:
        # An old preview must not authorize a newly edited space or budget.
        try:
            if params != self._search_params():
                return
        except ValueError:
            return
        self.preview, self._preview_request = result, params
        self.query_one("#exp-create", Button).disabled = not result.get("ready", True)
        self.query_one("#exp-preview-summary", Static).update(Text(
            f"{result.get('candidate_count', len(result.get('candidates', [])))} valid configurations · "
            f"{result.get('evaluations', result.get('evaluation_count', '?'))} evaluations · "
            f"{result.get('window_count', '?')} windows\n"
            f"Skipped data: {_config(result.get('skipped') or {}) or 'none'}\n"
            "Exploration uses train/validation only. Final holdout needs explicit validation after freezing the pick."))
        table = self.query_one("#exp-preview-table", DataTable)
        table.clear()
        for index, candidate in enumerate(result.get("candidates", [])):
            table.add_row(str(candidate.get("id", index)), _config(candidate.get("config", candidate)))

    @on(Button.Pressed, "#exp-create")
    def create_search(self) -> None:
        if self._preview_request is None or self._preview_request != self._search_params():
            self._invalidate()
            return
        self.query_one("#exp-create", Button).disabled = True
        self._command("experiments.create", self._preview_request, self._created)

    def _created(self, run: dict[str, Any]) -> None:
        self.run_id = run["id"]
        self.query_one("#exp-tabs", TabbedContent).active = "exp-explorer"
        self._command("experiments.start", {"run_id": self.run_id}, self._loaded_run)
        self.refresh_runs()

    @on(Button.Pressed, "#exp-refresh")
    def refresh_runs(self) -> None:
        self._command("experiments.list", {}, self._listed, quiet=True)

    def _listed(self, runs: list[dict[str, Any]]) -> None:
        self.runs = runs
        self._render_runs()

    def _render_runs(self) -> None:
        if not self.is_attached:
            return
        table = self.query_one("#exp-run-table", DataTable)
        table.clear()
        needle = self._input("exp-run-filter").lower()
        for run in self.runs:
            spec = run["spec"]
            source = spec.get("source", "native")
            if needle and needle not in f"{run['id']} {source} {run['status']}".lower():
                continue
            table.add_row(run["id"], source, str(spec.get("bot", "unknown")), run["status"],
                          _number(run.get("updated_at")), key=run["id"])

    @on(DataTable.RowSelected, "#exp-run-table")
    def selected_run(self, event: DataTable.RowSelected) -> None:
        self.run_id = str(event.row_key.value)
        self.selected_candidate = ""
        self._command("experiments.get", {"run_id": self.run_id}, self._loaded_run)

    def _loaded_run(self, run: dict[str, Any]) -> None:
        self._polling = False
        if run["id"] != self.run_id:
            return
        different_run = self.run.get("id") != run["id"]
        self.run = run
        spec = run["spec"]
        native = spec.get("source", "native") == "native"
        active = bool(run.get("worker_active"))
        self.query_one("#exp-resume", Button).disabled = not native or active or run["status"] == "completed"
        self._final_control()
        for name in ("pause", "cancel"):
            self.query_one(f"#exp-{name}", Button).disabled = not native or run["status"] == "completed"
        summary = run.get("summary") or {}
        verdict = summary.get("verdict") or {}
        progress = run.get("progress") or {}
        self.query_one("#exp-run-detail", Static).update(Text(
            f"{run['id']} · {spec.get('source', 'native')} · {run['status']} · worker {'active' if active else 'inactive'}\n"
            f"Progress: {_config(progress) if isinstance(progress, dict) else progress}\n"
            f"Decision: {verdict.get('reason', summary.get('reason', 'exploration only; final holdout sealed'))}\n"
            f"Error: {run.get('error') or 'none'}\n"
            f"Provenance: {_config({k: v for k, v in spec.items() if 'fingerprint' in k or k in ('costs', 'data_source', 'interval')})}\n"
            f"Diagnostic log: {run.get('log_path') or 'none'}\n{run.get('log_tail') or ''}"))
        candidates = spec.get("candidates") or []
        if candidates and different_run:
            first = candidates[0].get("config", candidates[0])
            self._axes(list(first))
        expected_id = self.run_id
        self._command("experiments.candidates", {"run_id": expected_id},
                      lambda rows: self._candidates_loaded(rows) if self.run_id == expected_id else None, quiet=True)

    @on(Checkbox.Changed, "#exp-adopt")
    def _final_control(self) -> None:
        if not self.run:
            return
        completed = self.run["status"] == "completed"
        verdict = (self.run.get("summary") or {}).get("verdict") or {}
        adopt = self.query_one("#exp-adopt", Checkbox).value
        allowed = (not completed or (adopt and verdict.get("reliable") and not verdict.get("adopted")))
        button = self.query_one("#exp-final", Button)
        button.disabled = (self.run["spec"].get("source", "native") != "native" or
                           bool(self.run.get("worker_active")) or not allowed)
        button.label = "Adopt validated pick" if completed and allowed else "Final validate"

    def _poll(self) -> None:
        if self._workbench_closed or self._polling or not self.run_id:
            return
        self._polling = True
        self._command("experiments.get", {"run_id": self.run_id}, self._loaded_run, quiet=True)

    def _candidates_loaded(self, rows: list[dict[str, Any]]) -> None:
        self.candidate_rows = rows
        self.render_candidates()

    @on(Select.Changed, "#exp-sort")
    def render_candidates(self) -> None:
        table = self.query_one("#exp-candidate-table", DataTable)
        table.clear()
        metric = self._selected("exp-sort")
        def med(row: dict, name: str) -> Any:
            return row.get("metrics", {}).get(name, {}).get("median")
        def key(row: dict) -> Any:
            if metric == "candidate_id":
                return (False, row["candidate_id"])
            value = med(row, metric)
            return (value is None, (value or 0) * (1 if metric == "max_drawdown" else -1))
        for row in sorted(self.candidate_rows, key=key):
            total = row.get("metrics", {}).get("total_return", {})
            table.add_row(row["candidate_id"], str(row["completed"]), str(row["failed"]),
                          _number(total.get("median")), _number(med(row, "max_drawdown")),
                          _number(med(row, "trades")), f"{_number(total.get('min'))} … {_number(total.get('max'))}",
                          key=row["candidate_id"])

    @on(DataTable.RowSelected, "#exp-candidate-table")
    def selected_candidate_row(self, event: DataTable.RowSelected) -> None:
        self.selected_candidate = str(event.row_key.value)
        row = next(r for r in self.candidate_rows if r["candidate_id"] == self.selected_candidate)
        self.query_one("#exp-candidate-detail", Static).update(Text(
            f"Candidate {self.selected_candidate}: {_config(row['config'])}\n"
            f"Observed coins: {', '.join(row.get('coins') or [])}; splits: {', '.join(row.get('splits') or [])}; "
            f"unbound imported rows: {row.get('unbound', row.get('undated', 0))}\n"
            + "\n".join(f"{name}: median {_number(m.get('median'))}, std dev {_number(m.get('stdev'))}, n={m.get('observations', 0)}"
                        for name, m in row.get("metrics", {}).items())))
        self.filter_cells()

    @on(Button.Pressed, "#exp-filter-cells")
    def filter_cells(self) -> None:
        if not self.run_id:
            return
        params = {"run_id": self.run_id}
        for name, value in (("coin", self._input("exp-cell-coin")), ("split", self._selected("exp-cell-split")),
                            ("candidate_id", self.selected_candidate)):
            if value:
                params[name] = value
        expected_id = self.run_id
        self._command("experiments.cells", params,
                      lambda rows: self._cells_loaded(rows) if self.run_id == expected_id else None, quiet=True)

    def _cells_loaded(self, cells: list[dict[str, Any]]) -> None:
        table = self.query_one("#exp-cell-table", DataTable)
        table.clear()
        self._shown_cells = {}
        status = self._selected("exp-cell-status")
        for index, cell in enumerate(cells):
            if status and cell["status"] != status:
                continue
            metrics = cell.get("metrics") or {}
            key = str(index)
            self._shown_cells[key] = cell
            table.add_row(cell["candidate_id"], cell["coin"], cell["split"], str(cell.get("start", "")),
                          str(cell.get("end", "")), cell["status"], _number(metrics.get("total_return")),
                          _number(metrics.get("max_drawdown")), _number(metrics.get("trades")),
                          str(cell.get("error") or ""), key=key)

    @on(DataTable.RowSelected, "#exp-cell-table")
    def selected_cell(self, event: DataTable.RowSelected) -> None:
        cell = self._shown_cells[str(event.row_key.value)]
        self.query_one("#exp-cell-detail", Static).update(Text(
            "\n".join(f"{name}: {_number(value)}" for name, value in cell.items())))

    def _control(self, action: str) -> None:
        if not self.run_id:
            return
        params: dict[str, Any] = {"run_id": self.run_id}
        if action == "finalize":
            params["adopt"] = self.query_one("#exp-adopt", Checkbox).value
        self._command(f"experiments.{action}", params, self._loaded_run)

    @on(Button.Pressed, "#exp-resume")
    def resume(self) -> None:
        self._control("start")

    @on(Button.Pressed, "#exp-pause")
    def pause(self) -> None:
        self._control("pause")

    @on(Button.Pressed, "#exp-cancel")
    def cancel(self) -> None:
        self._control("cancel")

    @on(Button.Pressed, "#exp-final")
    def finalize(self) -> None:
        self._control("finalize")

    @on(Button.Pressed, "#exp-heatmap")
    def heatmap(self) -> None:
        if not self.run_id:
            return
        params = {"run_id": self.run_id, "x": self._selected("exp-map-x"), "y": self._selected("exp-map-y"),
                  "metric": self._selected("exp-map-metric")}
        if self._input("exp-map-coin"):
            params["coin"] = self._input("exp-map-coin")
        if self._selected("exp-map-split"):
            params["split"] = self._selected("exp-map-split")
        expected_id = self.run_id
        self._command("experiments.heatmap", params,
                      lambda result: self._mapped(result) if self.run_id == expected_id else None)

    def _mapped(self, result: dict[str, Any]) -> None:
        self._map = result
        groups = result.get("groups", [])
        selector = self.query_one("#exp-map-group", Select)
        selector.set_options([(_config(group["fixed"]) or "No other parameters", str(i)) for i, group in enumerate(groups)])
        if groups:
            selector.value = "0"
            self._render_map()
        else:
            self.query_one("#exp-map-summary", Static).update(Text("No observed conditioned slices."))

    @on(Select.Changed, "#exp-map-group")
    def _render_map(self) -> None:
        choice = self._selected("exp-map-group")
        if not choice or not hasattr(self, "_map"):
            return
        group = self._map["groups"][int(choice)]
        self.query_one("#exp-map-summary", Static).update(Text(
            f"{self._map['split']} · {self._map['metric']} · {group['observed_points']}/{group['possible_points']} "
            f"observed points ({group['coverage']:.0%} coverage). No interpolation; holdout excluded.\n"
            f"Fixed: {_config(group['fixed'])}"))
        table = self.query_one("#exp-map-table", DataTable)
        table.clear(columns=True)
        table.add_columns(self._map["y"] + " ↓ / " + self._map["x"] + " →", *map(str, group["x_values"]))
        points = group["points"]
        observed = [p["value"] for p in points if p["value"] is not None]
        low, high = (min(observed), max(observed)) if observed else (0, 0)
        for y in group["y_values"]:
            values: list[Any] = [str(y)]
            for x in group["x_values"]:
                point = next((p for p in points if p["x"] == x and p["y"] == y), None)
                if not point or point["value"] is None:
                    values.append(Text("·", style="dim"))
                else:
                    fraction = (point["value"] - low) / (high - low) if high > low else 0.5
                    if self._map["metric"] == "max_drawdown":
                        fraction = 1 - fraction
                    color = "green" if fraction > .66 else "red" if fraction < .33 else "yellow"
                    values.append(Text(_number(point["value"]), style=color))
            table.add_row(*values)
        detail = self.query_one("#exp-map-points", DataTable)
        detail.clear()
        for point in points:
            detail.add_row(*[_number(point.get(name)) for name in ("x", "y", "value", "observations", "stdev", "min", "max", "failed")])

    @on(Button.Pressed, "#exp-import")
    def import_csv(self) -> None:
        metadata: dict[str, Any] = {"bot": self.bot}
        for name in ("coin", "interval", "currency", "script", "start", "end", "fee_bps", "slippage_bps",
                     "borrow_bps_per_day", "fill_delay", "strategy", "data_source", "label"):
            value = self._input(f"exp-meta-{name}")
            if not value:
                continue
            try:
                metadata[name] = (int(value) if name == "fill_delay" else float(value)) if name in {
                    "fee_bps", "slippage_bps", "borrow_bps_per_day", "fill_delay"} else value
            except ValueError:
                self.query_one("#exp-status", Static).update(Text(f"{name} must be a valid number."))
                return
        for name in ("return_unit", "drawdown_unit"):
            value = self._selected(f"exp-meta-{name}")
            if value:
                metadata[name] = value
        self._command("experiments.import", {"path": self._input("exp-import-path"), "metadata": metadata}, self._imported)

    def _imported(self, run: dict[str, Any]) -> None:
        self.run_id = run["id"]
        self.query_one("#exp-compare-left", Input).value = self.run_id
        self.query_one("#exp-compare-summary", Static).update(Text(
            f"Imported {self.run_id}. This evidence has no native adoption path. Enter a second run ID to compare provenance."))
        self.refresh_runs()
        self._command("experiments.get", {"run_id": self.run_id}, self._loaded_run, quiet=True)

    @on(Button.Pressed, "#exp-compare")
    def compare(self) -> None:
        self._command("experiments.compare", {"left": self._input("exp-compare-left") or self.run_id,
                                               "right": self._input("exp-compare-right")}, self._compared)

    def _compared(self, result: dict[str, Any]) -> None:
        verdict = "Comparable evidence" if result["comparable"] else "Not comparable"
        verdict += " · drawdown views use nonnegative loss fractions; reported source signs remain preserved"
        self.query_one("#exp-compare-summary", Static).update(Text(verdict + "\n" + "\n".join(result.get("reasons") or [])))
        table = self.query_one("#exp-compare-table", DataTable)
        table.clear()
        left, right = result.get("left_context") or {}, result.get("right_context") or {}
        for name in sorted(set(left) | set(right)):
            table.add_row(name, _number(left.get(name)), _number(right.get(name)),
                          "yes" if left.get(name) is not None and left.get(name) == right.get(name) else "unknown / differs")
        lines = []
        for side in ("left", "right"):
            lines.append(f"{side.title()} candidates (observed exploration evidence):")
            for row in result.get(f"{side}_candidates") or []:
                metrics = {k: v.get("median") for k, v in row.get("metrics", {}).items()}
                lines.append(f"  {row['candidate_id']}: {_config(row['config'])}; {_config(metrics)}")
        self.query_one("#exp-compare-detail", Static).update(Text("\n".join(lines)))

    @on(Button.Pressed, "#exp-close")
    def action_close(self) -> None:
        self._workbench_closed = True
        if self._timer:
            self._timer.stop()
        self.dismiss(None)

    def on_unmount(self) -> None:
        self._workbench_closed = True
        if self._timer:
            self._timer.stop()
