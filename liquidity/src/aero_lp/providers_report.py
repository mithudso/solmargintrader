"""Markdown report for `aero-lp providers` (providers-report.md). Pure formatting: no I/O, no network."""

from __future__ import annotations

import time
from typing import Any


def _pct(x: float | None, signed: bool = False, digits: int = 1) -> str:
    if x is None:
        return "n/a"
    return f"{x:+.{digits}f}%" if signed else f"{x:.{digits}f}%"


def _usd(x: float | None) -> str:
    if x is None:
        return "n/a"
    if x >= 1e9:
        return f"${x / 1e9:.2f}B"
    if x >= 1e6:
        return f"${x / 1e6:.2f}M"
    if x >= 1e3:
        return f"${x / 1e3:.0f}k"
    return f"${x:.0f}"


def _ratio(x: float | None) -> str:
    return "n/a" if x is None else f"{min(x, 999):.2f}"


def _cell(s: Any) -> str:
    return str(s).replace("|", "/").replace("\n", " ")


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out.extend("| " + " | ".join(_cell(c) for c in r) + " |" for r in rows)
    return out


def provider_table(doc: dict[str, Any]) -> list[str]:
    rows = []
    for s in doc.get("providers", []):
        b = s.get("best_pool")
        best = (
            f"{b['pair']} {_pct(b['expected_net_apr'], True)} ({b['tier']}, {b['confidence']})"
            if b and b.get("expected_net_apr") is not None
            else "n/a"
        )
        rows.append(
            [
                s["provider"],
                s["amm_type"],
                f"{s['pools_discovered']} / {s['pools_measured']} / {s['pools_quoted']}",
                _usd(s["tvl_usd"]),
                _pct(s.get("median_quoted_apy")) + " (quoted)" if s.get("median_quoted_apy") is not None else "n/a",
                _ratio(s.get("median_measured_edge")) if s.get("median_measured_edge") is not None else "n/a",
                best,
            ]
        )
    return _table(
        [
            "Provider",
            "AMM type",
            "Pools: found / measured / quoted",
            "TVL (found)",
            "Median APY",
            "Median measured edge",
            "Best pool: net APR",
        ],
        rows,
    )


def pool_table(doc: dict[str, Any], top: int = 25) -> list[str]:
    rows = []
    for i, p in enumerate(doc.get("pools", [])[:top], 1):
        measured = p["tier"] == "measured"
        inc = p.get("income_apr")
        rows.append(
            [
                str(i),
                p["venue"],
                p["pair"],
                f"{p['fee_pct']:.3g}%" if p.get("fee_pct") is not None else "n/a",
                p["tier"],
                p["confidence"],
                _usd(p["tvl_usd"]),
                (_pct(inc) + (" measured" if measured else " quoted")) if inc is not None else "n/a",
                _pct(p.get("quoted_apy_base")),
                _pct(p.get("incentive_apr")),
                _pct(p.get("lvr_apr")),
                _ratio(p.get("edge_ratio")),
                _pct(p.get("expected_net_apr"), True),
                _pct(p.get("replay_net_apr"), True) if measured else "n/a",
                "yes" if p.get("clears_bar") else "no",
            ]
        )
    return _table(
        [
            "#",
            "Provider",
            "Pair",
            "Fee",
            "Tier",
            "Confidence",
            "TVL",
            "Income APR",
            "DefiLlama quoted APY",
            "Incentive APR (separate)",
            "LVR APR",
            "Edge",
            "Net APR (expected)",
            "Replay net APR",
            "Clears bar",
        ],
        rows,
    )


HOW_TO_READ = """\
**Measured and quoted are different things.**
- *Measured* (Tier 1) rows read the pool on chain. Income is the change in `feeGrowthGlobal0/1X128` over the last 24
  hours, per unit of active liquidity. It already contains the real fee tier, dynamic fees, and who traded. The
  pool is then judged with the same LVR model, width optimizer and price-path replay the Aero scout uses.
- *Quoted* (Tier 2) rows have no on-chain reading here. Their income is DefiLlama's `apyBase`, a number computed
  from volume times the fee tier. On Aero such quotes overstated realized income about 5 times. A quoted row is
  capped at medium confidence, and many are low. Treat it as a lead to check, not as a result.
- The *DefiLlama quoted APY* column sits beside the income so the gap is visible. The two are not the same quantity:
  the quote spreads a pool's fees over all of its TVL, while the income column is what a deposit of this size earns
  at the best range width.
- *Incentive APR* (DefiLlama `apyReward`, for example Merkl or protocol emissions) has its own column. It is
  never added to income, because it ends when the program ends. The net APR column excludes it. The one
  exception is an Aero row staked in its gauge: its AERO emissions are measured on chain and are part of income, and the
  row says so.

**AERO price.** AERO income is valued at the spot price and does not account for emission dilution.

**Why an edge below 1 loses.** LVR is what informed traders take from a pool when the price moves. It is
sigma^2 / (8 (1 - e^(-w/2))) of the deposit per day for a +/-w range, and sigma^2 / 8 for a 50/50 constant-product
pool. The *edge ratio* is income divided by LVR. Narrowing the range raises income and LVR together, so the ratio
hardly depends on width. If it is below 1, no passive range makes money before costs, whatever the quoted APY says.

**The bar.** The allocator deploys only where the model net APR and the price-path replay both reach
"""
HOW_TO_READ_2 = """\
 after LVR and rebalance costs, the edge is at least 1.2, confidence is at least medium, and the numbers are
measured. A quoted row cannot clear it. The "Clears bar" column applies that rule to this deposit size.

**What else to check.** Small deposits die by gas: see the break-even deposit in `providers.json`. A pool with a hook
(Uniswap v4) can redirect fees. An unlisted token raises rug and price-feed risk, and lowers confidence. Rows with
low confidence are listed last. The sigma behind LVR comes from hourly prices (GeckoTerminal, else DefiLlama).
"""


def single_sided_tables(doc: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for tok, rows in doc.get("single_sided", {}).items():
        out += [f"**{tok}**", ""]
        if not rows:
            out += ["No single-sided pool with a positive base APY above the TVL minimum.", ""]
            continue
        out += _table(
            [
                "Project",
                "Asset",
                "Kind",
                "Excess over holding (apyBase)",
                "Incentive APR (separate)",
                "TVL",
                "Bar",
                "Risks the number leaves out",
            ],
            [
                [
                    r["project"],
                    r["asset"],
                    r["kind"],
                    _pct(r["apy_base"]) + " quoted",
                    _pct(r.get("apy_reward")),
                    _usd(r["tvl_usd"]),
                    "clears" if r.get("clears_bar") else "below",
                    r["risks"],
                ]
                for r in rows
            ],
        )
        out.append("")
    return out


def comparison_table(doc: dict[str, Any]) -> list[str]:
    rows = []
    for c in doc.get("comparison", []):
        lp, ss = c.get("best_lp"), c.get("best_single")
        rows.append(
            [
                c["token"],
                f"{lp['pair']} on {lp['venue']}: {_pct(lp['expected_net_apr'], True)} "
                f"({lp['tier']}, {lp['confidence']})" + (" clears" if lp["clears_bar"] else " below bar")
                if lp
                else "none",
                f"{ss['asset']} on {ss['project']}: {_pct(ss['apy_base'])} quoted ({ss['kind']})"
                + (" clears" if ss["clears_bar"] else " below bar")
                if ss
                else "none",
            ]
        )
    return _table(["Token", "Best LP net APR", "Best single-sided APR"], rows)


def render_report(doc: dict[str, Any], top: int = 25) -> str:
    when = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(doc["generated_at"]))
    pools = doc.get("pools", [])
    n_meas = sum(1 for p in pools if p["tier"] == "measured")
    n_quo = len(pools) - n_meas
    p = doc.get("params", {})
    bar = f"{doc['min_net_apr']:g}%" if doc.get("min_net_apr") is not None else "n/a"
    out = [
        f"# Liquidity provider comparison, {doc.get('chain', 'base')}",
        "",
        f"Generated {when} for a ${doc['deposit_usd']:,.0f} deposit. {len(pools)} pools scored: "
        f"{n_meas} measured on chain, {n_quo} quoted. Run took {p.get('elapsed_s', 0):.0f} s.",
        "",
        "## 1. Provider summary",
        "",
        "Median APY is DefiLlama's quoted figure for every pool found. Median measured edge uses only pools read on "
        "chain. Best pool is the first row of the ranking below for that provider.",
        "",
        *provider_table(doc),
        "",
        f"## 2. Top {min(top, len(pools))} pools by expected net APR",
        "",
        "Net APR is income minus LVR minus rebalance cost, before incentives. Low-confidence rows are last. "
        "Quoted income is labelled `quoted`.",
        "",
        *pool_table(doc, top),
        "",
        "## 3. How to read this",
        "",
        HOW_TO_READ + f"{bar} APR" + HOW_TO_READ_2,
    ]
    inc = doc.get("incentive_only", [])
    out += [
        "## 4. Single-sided yield on Base (comparison only)",
        "",
        "Pools with one asset and no impermanent-loss risk: lending supply and LST/LRT staking. The excess over just "
        "holding the token is the supply APY (lending) or the staking yield (LST, listed under WETH). Both are quotes "
        "from DefiLlama `apyBase`, not measured. The numbers leave out depeg, bad debt and contract risk. Nothing "
        "acts on these rows.",
        "",
        "Side by side, best LP against best single-sided option per token. The LP figure is for a pair that contains "
        f"the token, so it also carries the other token's price risk. The {bar} bar applies to both.",
        "",
        *comparison_table(doc),
        "",
        *single_sided_tables(doc),
    ]
    if inc:
        out += [
            "Incentive-only LP pools (rewards quoted, no base fee APY; not scored):",
            "",
            *_table(
                ["Project", "Pair", "TVL", "Incentive APR"],
                [[i["project"], i["pair"], _usd(i["tvl_usd"]), _pct(i["apy_reward"])] for i in inc[:15]],
            ),
            "",
        ]
    excl = doc.get("excluded", [])
    unscored = doc.get("unscored", [])
    errors = doc.get("errors", [])
    out += ["## 5. Coverage and caveats", ""]
    if excl:
        out += [
            "Excluded before scoring:",
            "",
            *_table(["Project", "Reason", "Rows"], [[e["project"], e["reason"], str(e["count"])] for e in excl]),
            "",
        ]
    if unscored:
        out += [
            "Found but not scored:",
            "",
            *_table(["Reason", "Rows"], [[u["reason"], str(u["count"])] for u in unscored]),
            "",
        ]
    if errors:
        out += ["Errors:", ""] + [f"- {e['pool']}: {e['error']}" for e in errors[:40]] + [""]
    out += ["Registry addresses read on chain:", ""]
    out += _table(
        ["Venue", "Factory / PoolManager", "Position manager", "Sources"],
        [
            [r["id"], r["factory"] or "n/a", r["position_manager"] or "n/a", "; ".join(r["sources"])]
            for r in doc.get("registry", [])
        ],
    )
    out.append("")
    return "\n".join(out)
