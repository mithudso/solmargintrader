"""Causal Coinbase visible-depth alignment for a separate ZEC diagnostic.

This does not equate Coinbase orderbook imbalance with Jupiter orders or fills.
"""

from __future__ import annotations

import math

from oracle_leverage.exit50 import signal_at


def diagnostic_candidates(
    prepared, models, feature_document, capture_start_ns, capture_end_ns
):
    """Return all eligible decisions and strict predecision qualified book facts."""
    if not isinstance(feature_document.get("rows"), list):
        raise TypeError("invalid_book_features")
    books = {}
    for row in feature_document["rows"]:
        at = row.get("decision_ns")
        if type(at) is not int or at in books:
            raise ValueError("invalid_book_decision")
        books[at] = row
    first = ((capture_start_ns // 1_000_000_000) // 600) * 600
    last = capture_end_ns // 1_000_000_000
    candidates = []
    for t in range(first, last + 661, 600):
        for family, at in (("near_end", t - 60), ("confirmed_uu", t)):
            decision_ns = at * 1_000_000_000
            if not capture_start_ns <= decision_ns <= capture_end_ns:
                continue
            signal = signal_at(prepared, at, family, models[family])
            if not signal["eligible"]:
                continue
            book = books.get(decision_ns, {"status": "no_book"})
            quote = book.get("quote_ns")
            value = book.get("imbalance")
            valid = (
                book.get("status") == "ready"
                and book.get("band_covered_by_visible_levels") is True
                and type(quote) is int
                and 0 <= decision_ns - quote <= 2_000_000_000
                and not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(value)
            )
            candidates.append(
                {
                    "id": f"ZEC:{family}:{at}",
                    "asset": "ZEC",
                    "family": family,
                    "decision_s": at,
                    "cap_s": t + 600,
                    "split": "capture",
                    "entry_price": None,
                    "signal": signal,
                    "book_status": "qualified"
                    if valid
                    else (
                        "invalid_book"
                        if book.get("status") == "ready"
                        else book.get("status", "invalid_book")
                    ),
                    "book_negative": value < 0 if valid else None,
                    "book_quote_ns": quote if valid else None,
                    "book_imbalance": value if valid else None,
                }
            )
    return candidates


def fetch_plan(plan_path, output_root, oracle_start, oracle_stop):
    """Fetch frozen diagnostic windows only inside archived Oracle history range."""
    import hashlib
    import json
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    from research.exit50_acquire import fetch_one
    from research.reversal_history import canonical

    path = Path(plan_path)
    plan = json.loads(path.read_text())
    if plan.get("schema") == "exit50-zec-l2-entry-plan/v1":
        slots = plan["slots"]
    elif plan.get("schema") == "exit50-zec-l2-lazy-plan/v1":
        slots = plan["selected_slots"]
    else:
        raise ValueError("invalid_diagnostic_plan")
    if len(slots) > 800 or len(slots) != len(set(slots)):
        raise ValueError("invalid_diagnostic_slots")
    if any(
        type(t) is not int or t % 120 or t - 60 < oracle_start or t + 60 > oracle_stop
        for t in slots
    ):
        raise ValueError("diagnostic_slot_outside_oracle_coverage")
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    jobs = [("ZEC", t, root) for t in slots]
    records = []

    def save():
        value = {
            "schema": "exit50-zec-l2-transport/v1",
            "plan_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "planned": len(jobs),
            "records": records,
        }
        raw = canonical(value) + "\n"
        temp = root / "manifest.pending"
        temp.write_text(raw)
        temp.replace(root / "manifest.json")
        return raw

    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, record in enumerate(pool.map(fetch_one, jobs), 1):
            records.append(record)
            if i % 50 == 0:
                save()
                print(f"{i}/{len(jobs)}", flush=True)
    raw = save()
    return {
        "planned": len(jobs),
        "complete": sum(r["status"] == 200 for r in records),
        "failed": sum(r["status"] != 200 for r in records),
        "manifest_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }


def load_archived_inputs(overlap_root, model_path):
    """Verify native-projected 1m page hashes and reconstruct causal context."""
    import hashlib
    import json
    from pathlib import Path

    from oracle_leverage.exit50 import prepare_signals
    from research.oracle_reversal_inputs import decode_history

    root = Path(overlap_root)
    receipt = json.loads((root / "zec-oracle-1m-receipt.json").read_text())
    rows = []
    for page in receipt["pages"]:
        raw = Path(page["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != page["sha256"]:
            raise ValueError("oracle_page_hash_mismatch")
        rows.extend(decode_history(json.loads(raw), page["from"], page["to_inclusive"]))
    model_bytes = Path(model_path).read_bytes()
    return (
        prepare_signals(rows),
        json.loads(model_bytes),
        receipt,
        hashlib.sha256(model_bytes).hexdigest(),
    )


def full_grid_position(c, features, get_minute, policy, delay):
    """Replay exact observed 200ms samples only through terminal, no OHLC skips."""
    from oracle_leverage.exit50 import GRID_US, start_position, step_position

    if c["entry_price"] is None:
        return {"status": "unscored", "reason": "missing_entry_sample"}
    first = c["decision_s"] * 1_000_000 + GRID_US
    state = start_position(
        first, c["entry_price"], c["cap_s"] * 1_000_000, policy, delay
    )
    while state["status"] == "open":
        next_us = state["last_us"] + GRID_US
        minute = next_us // 60_000_000 * 60
        points = get_minute(minute)
        if points is None:
            return {
                "status": "unscored",
                "reason": "incomplete_or_invalid_grid",
                "at_us": next_us,
            }
        try:
            for at, price in points:
                if at < next_us:
                    continue
                if at == first and price != c["entry_price"]:
                    return {
                        "status": "unscored",
                        "reason": "entry_price_conflict",
                        "at_us": at,
                    }
                state = step_position(state, at, price, features.get(at))
                if state["status"] != "open":
                    return state
        except (ValueError, TypeError):
            return {
                "status": "unscored",
                "reason": "incomplete_or_invalid_grid",
                "at_us": state["last_us"] + GRID_US,
            }
        end_us = (minute + 60) * 1_000_000 - GRID_US
        if state["last_us"] != end_us:
            return {
                "status": "unscored",
                "reason": "incomplete_or_invalid_grid",
                "at_us": state["last_us"] + GRID_US,
            }
    return state


def load_diagnostic_candidates(overlap_root, entry_root):
    """Bind frozen capture candidates to their verified entry grid samples."""
    import json
    from pathlib import Path

    from research.exit50_run import price_int, slot_data

    source = json.loads((Path(overlap_root) / "zec-l2-entry-plan.json").read_text())
    candidates = source["candidates"]
    for c in candidates:
        slot = c["decision_s"] + (60 if c["family"] == "near_end" else 0)
        points = slot_data(entry_root, "ZEC", slot)
        tick = next(
            (
                x
                for x in (points or [])
                if x["publish_time_us"] == c["decision_s"] * 1_000_000 + 200_000
            ),
            None,
        )
        c["entry_price"] = price_int(tick["price"]) if tick else None
    return candidates


def diagnostic_lazy_plan(overlap_root, entry_root, cache_root, model_path):
    """Return all 12 exit/delay proof states for the frozen capture cohort."""
    import hashlib
    import json
    from pathlib import Path

    from research.exit50_run import minute_reader

    root = Path(overlap_root)
    prepared, _bundle, receipt, model_sha = load_archived_inputs(root, model_path)
    entry_plan_bytes = (root / "zec-l2-entry-plan.json").read_bytes()
    candidates = load_diagnostic_candidates(root, entry_root)
    get_minute = minute_reader("ZEC", entry_root, cache_root)
    features = {
        stamp * 1_000_000: value for stamp, value in prepared["features"].items()
    }
    cases = []
    slots = set()
    permanent = []
    for c in candidates:
        entry_slot = c["decision_s"] + (60 if c["family"] == "near_end" else 0)
        entry_meta = Path(entry_root) / f"ZEC-{entry_slot}.meta.json"
        entry_sha = (
            json.loads(entry_meta.read_text()).get("sha256")
            if entry_meta.exists()
            else None
        )
        for policy in ("fixed", "second_turn", "target", "target_momentum"):
            for delay in (0, 5, 10):
                used = {entry_sha} if entry_sha else set()

                def tracked(minute, used=used):
                    slot = ((minute + 119) // 120) * 120
                    meta = Path(cache_root) / f"ZEC-{slot}.meta.json"
                    if not meta.exists():
                        meta = Path(entry_root) / f"ZEC-{slot}.meta.json"
                    if meta.exists():
                        sha = json.loads(meta.read_text()).get("sha256")
                        if sha:
                            used.add(sha)
                    return get_minute(minute)

                outcome = full_grid_position(c, features, tracked, policy, delay)
                record = {
                    "id": c["id"],
                    "policy": policy,
                    "delay": delay,
                    "source_sha256": sorted(used),
                }
                if outcome["status"] != "unscored":
                    record.update(state="terminal", terminal_us=outcome["exit_us"])
                elif outcome["reason"] == "incomplete_or_invalid_grid":
                    minute = outcome["at_us"] // 60_000_000 * 60
                    slot = ((minute + 119) // 120) * 120
                    known = (Path(cache_root) / f"ZEC-{slot}.meta.json").exists() or (
                        Path(entry_root) / f"ZEC-{slot}.meta.json"
                    ).exists()
                    if known:
                        record.update(
                            state="unscored",
                            reason="existing_grid_gap",
                            at_us=outcome["at_us"],
                        )
                        permanent.append(record)
                    else:
                        record.update(state="need_source", slot=slot)
                        slots.add(slot)
                else:
                    record.update(state="unscored", reason=outcome["reason"])
                    permanent.append(record)
                cases.append(record)
    demand = {
        "checked": len(cases),
        "slots": sorted(slots),
        "permanent": permanent,
        "cases": cases,
    }
    value = {
        "schema": "exit50-zec-l2-lazy-plan/v1",
        "candidate_count": len(candidates),
        "checked": demand["checked"],
        "all_needed_count": len(demand["slots"]),
        "selected_slots": demand["slots"][:800],
        "permanent": demand["permanent"],
        "cases": demand["cases"],
        "entry_plan_sha256": hashlib.sha256(entry_plan_bytes).hexdigest(),
        "model_sha256": model_sha,
        "oracle_pages_sha256": [p["sha256"] for p in receipt["pages"]],
    }
    return value


def evaluate_diagnostic(prepared, candidates, entry_root, cache_root, proof_plan):
    """Evaluate book-qualified cohorts separately; never feed paper selection."""
    from research.exit50_run import minute_reader, summarize, summarize_paired
    from research.reversal_shapes import color

    if (
        proof_plan.get("schema") != "exit50-zec-l2-lazy-plan/v1"
        or proof_plan.get("candidate_count") != len(candidates)
        or proof_plan.get("all_needed_count") != 0
        or proof_plan.get("selected_slots")
        or len(proof_plan.get("cases", [])) != len(candidates) * 12
        or any(
            c.get("state") not in ("terminal", "unscored") for c in proof_plan["cases"]
        )
    ):
        raise ValueError("diagnostic_source_proof_incomplete")
    features = {
        stamp * 1_000_000: value for stamp, value in prepared["features"].items()
    }
    ten = {bar[0]: bar for bar in prepared["frames"]["10"][0]}
    get_minute = minute_reader("ZEC", entry_root, cache_root)
    variants = []
    for family in ("confirmed_uu", "near_end"):
        rows = [c for c in candidates if c["family"] == family]
        for policy in ("fixed", "second_turn", "target", "target_momentum"):
            for delay in (0, 5, 10):
                cohorts = {}
                for group in ("all", "qualified", "negative", "complement"):
                    until = -1
                    overlap = 0
                    records = []
                    for c in rows:
                        if group != "all" and c["book_status"] != "qualified":
                            continue
                        if group == "negative" and c["book_negative"] is not True:
                            continue
                        if group == "complement" and c["book_negative"] is not False:
                            continue
                        if c["decision_s"] * 1_000_000 < until:
                            overlap += 1
                            continue
                        target_start = c["decision_s"] + (
                            60 if family == "near_end" else 0
                        )
                        bar = ten.get(target_start)
                        if c["entry_price"] is None:
                            result = {
                                "status": "unscored",
                                "reason": "missing_entry_sample",
                            }
                        else:
                            result = full_grid_position(
                                c, features, get_minute, policy, delay
                            )
                        until = (
                            result.get("exit_us") or (c["cap_s"] + delay) * 1_000_000
                        )
                        records.append(
                            {
                                "id": c["id"],
                                "split": "capture",
                                "bar3_color": color(bar) if bar else "UNKNOWN",
                                "partial_second_direction": c["signal"][
                                    "partial_second_direction"
                                ],
                                "outcome": result,
                            }
                        )
                    cohorts[group] = {
                        "records": records,
                        "summary": summarize(records),
                        "overlap_skips": overlap,
                    }
                cohorts["same_entry_qualified_vs_negative"] = summarize_paired(
                    cohorts["negative"]["records"], cohorts["qualified"]["records"]
                )
                # Book status only filters entries; on the identical timestamps,
                # no-book and negative-book have the same entry/exit rule.
                matched = summarize(cohorts["negative"]["records"])
                cohorts["same_negative_entries_no_book_counterfactual"] = {
                    "negative_book": matched,
                    "no_book": matched,
                    "qualification": "same entries and exit policy; counterfactual may overlap when replayed independently",
                }
                variants.append(
                    {
                        "family": family,
                        "exit": policy,
                        "delay_seconds": delay,
                        "cohorts": cohorts,
                    }
                )
    return variants
