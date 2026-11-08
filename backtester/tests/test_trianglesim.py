"""Triangular-arbitrage replay: rate direction, the card's worked example, and latency."""

from __future__ import annotations

import math
import unittest

from backtester.core.trianglesim import (
    SOURCE_CANDLE_PROXY,
    Triangle,
    TriangleConfig,
    cycle_edges_bps,
    run_triangle_backtest,
    snapshots_from_closes,
    triangles_from_products,
)

TRI = Triangle("ETH", "BTC")  # ETH-USD, BTC-USD, ETH-BTC


def q(bid, ask, t=0.0, bsz=None, asz=None):
    return (float(bid), float(ask), bsz, asz, float(t))


def parity(t=0.0, dislocation=1.0):
    """ETH 3000, BTC 60000, ETH-BTC 0.05 x dislocation, zero spread."""
    return {"ETH-USD": q(3000, 3000, t), "BTC-USD": q(60000, 60000, t),
            "ETH-BTC": q(0.05 * dislocation, 0.05 * dislocation, t)}


class Edges(unittest.TestCase):
    def test_a_consistent_book_has_zero_gross_edge_both_ways(self) -> None:
        fwd, rev = cycle_edges_bps(TRI, parity(), fee_bps=0.0)
        self.assertAlmostEqual(fwd, 0.0, places=9)
        self.assertAlmostEqual(rev, 0.0, places=9)

    def test_the_users_ninety_nine_cycle_loses(self) -> None:
        # Card: 1 ETH -> 1 ZEC -> 1.1 BTC -> 0.99 ETH, here as USD -> A -> B -> USD.
        quotes = {"ETH-USD": q(1.0, 1.0), "BTC-USD": q(0.9, 0.9), "ETH-BTC": q(1.1, 1.1)}
        fwd, _ = cycle_edges_bps(TRI, quotes, fee_bps=0.0)
        self.assertAlmostEqual(fwd, -100.0, places=6)

    def test_the_cards_positive_example(self) -> None:
        # Card: M_gross 1.012 with 10 bps per leg -> net 89.67034988 bps.
        quotes = {"ETH-USD": q(1.0, 1.0), "BTC-USD": q(0.92, 0.92), "ETH-BTC": q(1.1, 1.1)}
        fwd, _ = cycle_edges_bps(TRI, quotes, fee_bps=10.0)
        self.assertAlmostEqual(fwd, 89.67034988, places=6)

    def test_rate_direction_rich_cross_pays_forward_cheap_cross_pays_reverse(self) -> None:
        fwd, rev = cycle_edges_bps(TRI, parity(dislocation=1.01), fee_bps=0.0)
        self.assertGreater(fwd, 99)  # selling ETH for too much BTC
        self.assertLess(rev, 0)
        fwd, rev = cycle_edges_bps(TRI, parity(dislocation=0.99), fee_bps=0.0)
        self.assertLess(fwd, 0)
        self.assertGreater(rev, 99)

    def test_the_spread_is_crossed_on_every_leg(self) -> None:
        quotes = {"ETH-USD": q(2999, 3001), "BTC-USD": q(59990, 60010), "ETH-BTC": q(0.04999, 0.05001)}
        fwd, rev = cycle_edges_bps(TRI, quotes, fee_bps=0.0)
        self.assertLess(fwd, 0)
        self.assertLess(rev, 0)

    def test_fees_need_about_thirty_bps_to_break_even(self) -> None:
        fwd, _ = cycle_edges_bps(TRI, parity(dislocation=1 / 0.999 ** 3), fee_bps=10.0)
        self.assertAlmostEqual(fwd, 0.0, places=6)

    def test_a_missing_or_stale_or_crossed_leg_is_unusable(self) -> None:
        book = parity(t=0.0)
        del book["ETH-BTC"]
        self.assertIsNone(cycle_edges_bps(TRI, book, 0.0))
        self.assertIsNone(cycle_edges_bps(TRI, parity(t=0.0), 0.0, now=10.0, max_age=5.0))
        crossed = parity()
        crossed["ETH-USD"] = q(3001, 3000)
        self.assertIsNone(cycle_edges_bps(TRI, crossed, 0.0))

    def test_triangles_are_found_from_a_product_list(self) -> None:
        tris = triangles_from_products(["ETH-USD", "BTC-USD", "SOL-USD", "ETH-BTC", "SOL-BTC", "XLM-BTC"])
        self.assertEqual([t.name for t in tris], ["USD-ETH-BTC", "USD-SOL-BTC"])


class SnapshotFiles(unittest.TestCase):
    def test_a_truncated_gzip_member_keeps_the_complete_lines(self) -> None:
        import gzip
        import json
        import tempfile
        from pathlib import Path

        from backtester.core.trianglesim import read_snapshot_files

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-11-08.jsonl.gz"
            good = [json.dumps({"t": t, "q": {"ETH-USD": [3000, 3001, 3000.5, 1, 2, t]}}) + "\n"
                    for t in (1.0, 2.0)]
            with gzip.open(path, "at", encoding="utf-8") as fh:
                fh.writelines(good)
            blob = gzip.compress((json.dumps({"t": 3.0, "q": {}}) + "\n").encode())
            with open(path, "ab") as fh:
                fh.write(blob[: len(blob) // 2])  # a crash mid-flush
            snaps = read_snapshot_files([path])
            self.assertEqual([t for t, _ in snaps], [1.0, 2.0])
            self.assertEqual(snaps[0][1]["ETH-USD"][:4], (3000.0, 3001.0, 1.0, 2.0))
            self.assertEqual(read_snapshot_files([path], start_ts=1.5)[0][0], 2.0)

    def test_crossed_or_garbage_quotes_are_dropped(self) -> None:
        from backtester.core.trianglesim import parse_snapshot_line

        self.assertIsNone(parse_snapshot_line("not json"))
        t, quotes = parse_snapshot_line('{"t": 5, "q": {"A-USD": [2, 1], "B-USD": ["x"], "C-USD": [1, 2]}}')
        self.assertEqual(t, 5.0)
        self.assertEqual(list(quotes), ["C-USD"])


class Replay(unittest.TestCase):
    def test_a_dislocation_that_vanishes_before_execution_is_a_loss(self) -> None:
        cfg = TriangleConfig(min_edge_bps=20, taker_fee_bps=10, latency_s=1.0)
        snaps = [(0.0, parity(0.0, 1.01)), (1.0, parity(1.0, 1.0))]
        r = run_triangle_backtest(cfg, snaps, [TRI])
        self.assertEqual(r.executed, 1)
        self.assertLess(r.pnl_usd, 0)
        self.assertAlmostEqual(r.cycles[0]["realized_edge_bps"], 10_000 * (0.999 ** 3 - 1))

    def test_a_persistent_dislocation_is_a_win(self) -> None:
        cfg = TriangleConfig(min_edge_bps=20, taker_fee_bps=10, latency_s=1.0, cooldown_s=100)
        snaps = [(0.0, parity(0.0, 1.01)), (1.0, parity(1.0, 1.01)), (2.0, parity(2.0, 1.01))]
        r = run_triangle_backtest(cfg, snaps, [TRI])
        self.assertEqual(r.executed, 1)  # cooldown suppresses a second cycle
        self.assertGreater(r.pnl_usd, 0)

    def test_no_execution_without_a_later_snapshot(self) -> None:
        r = run_triangle_backtest(TriangleConfig(min_edge_bps=20), [(0.0, parity(0.0, 1.01))], [TRI])
        self.assertEqual(r.executed, 0)
        self.assertEqual(r.per_triangle[TRI.name]["signals"], 1)

    def test_size_is_capped_by_the_touch(self) -> None:
        cfg = TriangleConfig(min_edge_bps=20, taker_fee_bps=0, latency_s=0.0, notional_usd=1000)
        book = parity(0.0, 1.01)
        book["ETH-USD"] = q(3000, 3000, 0.0, bsz=1.0, asz=0.01)  # 0.01 ETH = $30 at the ask
        r = run_triangle_backtest(cfg, [(0.0, book)], [TRI])
        self.assertAlmostEqual(r.cycles[0]["notional_usd"], 30.0)

    def test_quotes_carry_forward_and_age_out(self) -> None:
        cfg = TriangleConfig(min_edge_bps=1e9, max_quote_age_s=5.0)
        snaps = [(0.0, parity(0.0)), (3.0, {"ETH-USD": q(3000, 3000, 3.0)}), (9.0, {})]
        r = run_triangle_backtest(cfg, snaps, [TRI])
        self.assertEqual(r.per_triangle[TRI.name]["observed"], 2)  # t=9 is stale

    def test_future_snapshots_cannot_change_past_signals_or_fills(self) -> None:
        cfg = TriangleConfig(min_edge_bps=20, taker_fee_bps=10, latency_s=1.0, cooldown_s=0)
        base = [(float(t), parity(float(t), 1.01 if t % 3 == 0 else 1.0)) for t in range(12)]
        changed = base[:8] + [(float(t), parity(float(t), 0.9)) for t in range(8, 12)]
        a = run_triangle_backtest(cfg, base, [TRI]).cycles
        b = run_triangle_backtest(cfg, changed, [TRI]).cycles
        early = lambda cycles: [c for c in cycles if c["exec_ts"] < 8]
        self.assertEqual(early(a), early(b))

    def test_streaming_equals_batch(self) -> None:
        from backtester.core.trianglesim import TriangleReplay

        cfg = TriangleConfig(min_edge_bps=20, taker_fee_bps=10, latency_s=1.5, cooldown_s=0.5)
        snaps = [(t * 0.5, parity(t * 0.5, 1.01 if t % 4 < 2 else 1.0)) for t in range(40)]
        batch = run_triangle_backtest(cfg, snaps, [TRI]).summary()
        replay = TriangleReplay(cfg, [TRI])
        for t, quotes in snaps[:17]:
            replay.feed(t, quotes)
        partial = replay.result().executed
        for t, quotes in snaps[17:]:
            replay.feed(t, quotes)
        self.assertEqual(replay.result().summary(), batch)
        self.assertLessEqual(partial, batch["executed"])
        self.assertGreater(batch["executed"], 0)

    def test_snapshots_must_be_ordered(self) -> None:
        with self.assertRaises(ValueError):
            run_triangle_backtest(TriangleConfig(), [(2.0, {}), (1.0, {})], [TRI])

    def test_candle_proxy_pairs_only_same_minute_legs_and_adds_spread(self) -> None:
        snaps = snapshots_from_closes(
            {"ETH-USD": [(60, 3000.0), (120, 3000.0)], "BTC-USD": [(60, 60000.0)],
             "ETH-BTC": [(60, 0.05), (120, 0.05)]}, half_spread_bps=5.0)
        self.assertEqual([t for t, _ in snaps], [60.0, 120.0])
        self.assertNotIn("BTC-USD", snaps[1][1])
        bid, ask = snaps[0][1]["ETH-USD"][:2]
        self.assertTrue(math.isclose(bid, 3000 * 0.9995) and math.isclose(ask, 3000 * 1.0005))
        r = run_triangle_backtest(TriangleConfig(), snaps, [TRI], source=SOURCE_CANDLE_PROXY)
        self.assertEqual(r.source, SOURCE_CANDLE_PROXY)
        # At t=120 the BTC-USD leg is the t=60 candle, 60 s old: stale, so not observed.
        self.assertEqual(r.per_triangle[TRI.name]["observed"], 1)

    def test_config_refuses_nonsense(self) -> None:
        for bad in ({"notional_usd": 0}, {"latency_s": -1}, {"taker_fee_bps": float("inf")}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                TriangleConfig(**bad)


if __name__ == "__main__":
    unittest.main()
