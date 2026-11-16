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


def diagnostic_lazy_plan(overlap_root, entry_root, cache_root, model_path):
    """Return all 12 exit/delay proof states for the frozen capture cohort."""
    import hashlib
    import json
    from pathlib import Path

    from research.exit50_run import first_missing_windows, price_int, slot_data

    root = Path(overlap_root)
    prepared, _bundle, receipt, model_sha = load_archived_inputs(root, model_path)
    entry_plan_bytes = (root / "zec-l2-entry-plan.json").read_bytes()
    source = json.loads(entry_plan_bytes)
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
    demand = first_missing_windows("ZEC", prepared, candidates, entry_root, cache_root)
    value = {
        "schema": "exit50-zec-l2-lazy-plan/v1",
        "candidate_count": len(candidates),
        "checked": demand["checked"],
        "all_needed_count": len(demand["slots"]),
        "selected_slots": [slot for _, slot in demand["slots"][:800]],
        "permanent": demand["permanent"],
        "cases": demand["cases"],
        "entry_plan_sha256": hashlib.sha256(entry_plan_bytes).hexdigest(),
        "model_sha256": model_sha,
        "oracle_pages_sha256": [p["sha256"] for p in receipt["pages"]],
    }
    return value
