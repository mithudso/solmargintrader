"""Rails: every limit an order must pass, as code. A rail documented but not enforced is not a rail.

All rails fail closed: a missing price, an unknown side, an unreadable record or a non-finite number is a refusal,
never a pass. `check_trade` returns every problem at once so a caller sees the whole picture. It is pure: the
caller supplies the journal states, the KILL flag, the clock and the balances.

Which rails apply:
  always (dry-run mirrors live):  side, max_trade_usd, max_position_usd, long-or-flat, daily loss stop, SOL reserve
  live only:                      mode + --live, KILL file, unresolved sends, research + soak gates, key file
  never for an exit (reduce-only sell of a tracked position): KILL, daily loss stop, gates, max_trade_usd.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal

from . import gates, ledger
from .config import VALIDATION_MAX_DAILY_USD, VALIDATION_MAX_TRADE_USD, VALIDATION_STRATEGY, Config
from .errors import Refused
from .journal import TERMINAL, Journal, failed_accounting_missing
from .quote import QuoteReport
from .tokens import QUOTE_MINT, WSOL_MINT, raw_to_ui


@dataclass(frozen=True)
class Decision:
    side: str | None  # buy | sell | None
    base_mint: str | None
    notes: tuple[str, ...]
    exit: bool
    gates_exempt: bool

    def to_dict(self) -> dict:
        return {"side": self.side, "base_mint": self.base_mint, "exit": self.exit, "notes": list(self.notes)}


def classify(report: QuoteReport) -> tuple[str | None, str | None]:
    """(side, base_mint). Spot against USDC only: USDC -> X is a buy of X, X -> USDC is a sell of X."""
    tin, tout = report.token_in, report.token_out
    if tin.mint == QUOTE_MINT and tout.mint != QUOTE_MINT and not tout.stable:
        return "buy", tout.mint
    if tout.mint == QUOTE_MINT and tin.mint != QUOTE_MINT and not tin.stable:
        return "sell", tin.mint
    return None, None


def check_trade(
    cfg: Config,
    root,
    journal: Journal,
    report: QuoteReport,
    *,
    strategy: str | None,
    live: bool,
    exit_only: bool,
    kill_present: bool,
    native_lamports: int,
    now: float | None = None,
) -> Decision:
    """Raise Refused listing every failed rail, or return the Decision."""
    now = time.time() if now is None else now
    r = cfg.rails
    problems: list[str] = []
    notes: list[str] = []
    side, base = classify(report)
    states = journal.states()
    is_validation = strategy == VALIDATION_STRATEGY

    # -- mode ---------------------------------------------------------------------------------------------
    if live:
        if cfg.mode != "live":
            problems.append('live was requested but config mode is not "live"')
        if not strategy:
            problems.append("a live swap needs a strategy id")
    if report.problems:
        problems.extend(f"quote: {p}" for p in report.problems)

    # -- strategy shape -----------------------------------------------------------------------------------
    if strategy and side is None:
        problems.append("strategy trades are spot USDC <-> base only (long or flat, no shorts)")
    if exit_only and side != "sell":
        problems.append("--exit is a reduce-only sell of a tracked position")
    if is_validation:
        if not cfg.validation.enabled:
            problems.append("strategy 'path-validation' needs [validation].enabled = true")
        if report.in_usd > Decimal(str(VALIDATION_MAX_TRADE_USD)):
            problems.append(f"path-validation trades are capped at ${VALIDATION_MAX_TRADE_USD:g} (code limit)")
        spent = ledger.trades_notional_usd(states, VALIDATION_STRATEGY, now - 86400)
        if spent + report.in_usd > Decimal(str(VALIDATION_MAX_DAILY_USD)):
            problems.append(f"path-validation is capped at ${VALIDATION_MAX_DAILY_USD:g} per rolling 24 h (code limit)")

    # -- position, size, loss stop ------------------------------------------------------------------------
    pos = ledger.Position()
    if strategy and base:
        pos = ledger.positions(states, strategy).get(base, ledger.Position())
    # path-validation may sell wallet SOL it did not buy (it proves the live path in either direction); its $2 code cap
    # bounds that. Every real strategy is long or flat.
    if side == "sell" and strategy and not is_validation and report.quote.in_raw > pos.qty_raw:
        problems.append(
            f"sell of {report.quote.in_raw} exceeds the strategy's open quantity {pos.qty_raw} (long or flat, no shorts)"
        )
    if exit_only:
        if not strategy:
            problems.append("--exit needs the strategy whose position it reduces")
        if pos.qty_raw <= 0 or report.quote.in_raw > pos.qty_raw:
            problems.append("--exit must reduce a tracked open quantity; wallet inventory alone is not a position")
    else:
        if report.in_usd > Decimal(str(r.max_trade_usd)):
            problems.append(f"trade value ${float(report.in_usd):.4f} exceeds max_trade_usd ${r.max_trade_usd:g}")
        if side == "buy" and strategy:
            after = pos.cost_usd + report.in_usd
            if after > Decimal(str(r.max_position_usd)):
                problems.append(
                    f"position would be ${float(after):.4f}, over max_position_usd ${r.max_position_usd:g} for '{strategy}'"
                )
            loss = _loss_today(states, strategy, base, report, pos, now)
            if loss >= Decimal(str(r.daily_loss_stop_usd)):
                problems.append(
                    f"daily loss ${float(loss):.4f} has reached daily_loss_stop_usd ${r.daily_loss_stop_usd:g}; no new buys today (UTC)"
                )

    # -- native SOL reserve (pre-check; the verifier re-checks against the simulated post-state) ----------
    needed = report.quote.in_raw if report.token_in.mint == WSOL_MINT else 0
    if report.token_out.mint != WSOL_MINT and native_lamports - needed < r.min_sol_reserve_lamports:
        problems.append(
            f"native SOL {native_lamports} lamports minus the input {needed} would fall below "
            f"min_sol_reserve_lamports {r.min_sol_reserve_lamports}"
        )

    # -- live-only rails -----------------------------------------------------------------------------------
    gates_exempt = is_validation and cfg.validation.enabled
    if live:
        if kill_present and not exit_only:
            problems.append("KILL file present: live swaps are halted (only --exit is allowed)")
        pending = journal.unresolved()
        proven_tracked_exit = (
            exit_only
            and not is_validation
            and strategy is not None
            and side == "sell"
            and 0 < report.quote.in_raw <= pos.qty_raw
        )
        if proven_tracked_exit:
            # A terminal failed attempt cannot land again. Its missing fee
            # blocks new risk, but cannot prevent a measured position reduction.
            # Actual sending/unknown records always retain the submit barrier.
            pending = [
                state for state in pending if state["state"] not in TERMINAL or not failed_accounting_missing(state)
            ]
        if pending:
            problems.append(f"unresolved send(s) {', '.join(p['id'] for p in pending)}: run `executor reconcile`")
        if journal.corrupt_lines():
            problems.append("the journal has an unparseable line")
        if strategy and not exit_only:
            if gates_exempt:
                notes.append(
                    "gates skipped: reserved strategy path-validation (code-capped at $2 per trade, $4 per 24 h)"
                )
            else:
                gate_problems, gate_notes = gates.check_live_allowed(root, cfg, strategy, now)
                problems.extend(gate_problems)
                notes.extend(gate_notes)

    if problems:
        raise Refused(problems)
    return Decision(side, base, tuple(notes), exit_only, gates_exempt)


def _loss_today(
    states, strategy: str, base: str | None, report: QuoteReport, pos: ledger.Position, now: float
) -> Decimal:
    """Positive number: realized loss + fees today (UTC), plus the open position's unrealized loss at the reference."""
    realized = ledger.realized_pnl_usd(states, ledger.utc_day(now), strategy)
    loss = max(Decimal(0), -realized)
    if base and pos.qty_raw > 0:
        tok = report.token_out if report.token_out.mint == base else report.token_in
        price = report.price_out_usd if report.token_out.mint == base else report.price_in_usd
        market = raw_to_ui(pos.qty_raw, tok.decimals) * price
        loss += max(Decimal(0), pos.cost_usd - market)
    return loss
