"""Causal execution, coverage and book-capacity regression gates."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from backtester.core.strategies import REGISTRY
from backtester.core.zec_ensemble import spec_id
from research.zec_granular import (
    NS,
    Book,
    Portfolio,
    frozen_catalog,
    make_bars,
    member_signals,
    policy_signal,
    prepare_capture,
    segments,
    spot_replay,
    volty_replay,
)


def fixture_tape(prices=(100, 101, 102, 103), times=None, size=1000):
    times = [61, 121, 181, 241] if times is None else times
    books = np.zeros((len(prices), 2, 40, 2))
    for i, price in enumerate(prices):
        books[i, 0, 0] = [price-0.1, size]
        books[i, 1, 0] = [price+0.1, size]
    return {"quote_ns": np.array(times, dtype=np.int64)*NS, "books": books,
            "trade_ns": np.array([1, 30, 65, 125, 185], dtype=np.int64)*NS,
            "price": np.array([99,100,101,102,103.]), "size": np.ones(5),
            "end_ns": 243*NS}


class GranularReplay(unittest.TestCase):
    def test_depth_orders_and_deleted_readded_price_not_double_counted(self):
        b = Book()
        b.snapshot({"bids": [[99, 1], [98, 2]], "asks": [[101, 1], [102, 2]]})
        b.update(1, 101, 0)
        b.update(1, 101, 3)
        self.assertEqual(b.levels(1), [(101, 3), (102, 2)])
        self.assertEqual(b.levels(0), [(99, 1), (98, 2)])

    def test_crossed_or_invalidated_book_refused(self):
        b = Book()
        b.snapshot({"bids": [[102, 1]], "asks": [[101, 1]]})
        self.assertIsNone(b.quote())
        b.valid = False
        self.assertIsNone(b.quote())

    def test_fills_cannot_precede_decision_plus_latency(self):
        p = Portfolio(fixture_tape(), 60)
        with self.assertRaisesRegex(ValueError, "eligibility"):
            p.target(1, 0, 61*NS)
        p.target(1, 0, 60*NS)
        self.assertGreater(p.fees, 0)
        self.assertGreaterEqual(p.cash, -1e-9)
        self.assertLessEqual(p.qty*100, 10000)

    def test_insufficient_depth_rejects_instead_of_inventing_fill(self):
        p = Portfolio(fixture_tape(size=0.01), 10)
        p.target(1, 0, 60*NS)
        self.assertEqual(len(p.fills), 0)
        self.assertEqual(p.rejections["insufficient_40_level_depth"], 1)

    def test_book_search_never_uses_previous_or_late_book(self):
        p = Portfolio(fixture_tape(), 10)
        self.assertEqual(p.quote_index(60*NS), 0)
        self.assertIsNone(p.quote_index(62*NS))
        self.assertIsNone(p.quote_index(300*NS))

    def test_receive_time_bars_partial_edges_and_gap_invalidation(self):
        tape = fixture_tape()
        info = {"start_ns": 0, "end_ns": 200*NS, "gaps": [[130*NS, 135*NS, "gap"]]}
        bars, valid, counts = make_bars(tape, info, 60)
        self.assertEqual(bars["ts"].tolist(), [60,120])
        self.assertEqual(valid.tolist(), [True,False])
        self.assertEqual(counts.tolist(), [1,1])
        self.assertEqual(bars["open"].tolist(), [101,102])

    def test_missing_trade_minute_is_not_interpolated(self):
        tape = fixture_tape()
        tape["trade_ns"] = np.array([65],dtype=np.int64)*NS
        tape["price"], tape["size"] = np.array([100.]), np.array([1.])
        _, valid, _ = make_bars(tape, {"start_ns":0,"end_ns":240*NS,"gaps":[]},60)
        self.assertEqual(valid.tolist(), [True,False,False])
        self.assertEqual(segments(valid), [(0,1)])

    def test_later_gap_detection_does_not_erase_a_closed_bar(self):
        tape=fixture_tape()
        info={"start_ns":0,"end_ns":200*NS,"gaps":[[119*NS,121*NS,"trade_id_gap"]]}
        _,valid,_=make_bars(tape,info,60)
        self.assertTrue(valid[0])
        self.assertFalse(valid[1])

    def test_ten_minute_interval_is_real_600_seconds(self):
        tape = fixture_tape()
        bars, _, _ = make_bars(tape,{"start_ns":0,"end_ns":2400*NS,"gaps":[]},600)
        self.assertEqual(bars["ts"].tolist(),[600,1200,1800])

    def test_signals_reset_after_gap_and_future_prices_cannot_change_prefix(self):
        n = 40
        a = {"ts":np.arange(n)*60, **{k:np.arange(n,dtype=float)+100 for k in ("open","high","low","close")}, "volume":np.ones(n)}
        spec = {"strategy":"ma_crossover","params":{"fast":2,"slow":4}}
        valid=np.ones(n,dtype=bool); valid[20]=False
        x, mask = member_signals(spec,a,valid,60)
        altered={k:v.copy() for k,v in a.items()}; altered["close"][30:]*=10
        y,_=member_signals(spec,altered,valid,60)
        np.testing.assert_equal(x[:30],y[:30])
        self.assertFalse(mask[21])
        self.assertTrue(mask[29])

    def test_closed_bar_uses_next_book_and_deadline_close_is_predeclared(self):
        tape=fixture_tape()
        p=spot_replay(tape,{"ts":np.array([0,60,120]),"step":60},np.array([1.,0.,0.]),10)
        self.assertEqual(p.fills[0]["fill_ns"],61*NS)
        self.assertEqual(p.fills[1]["fill_ns"],121*NS)
        self.assertEqual(p.qty,0)
        self.assertLess(p.result()["end_equity"], 10100)

    def test_cash_is_cash_not_strategy_success(self):
        tape=fixture_tape()
        p=spot_replay(tape,{"ts":np.array([0,60,120]),"step":60},np.full(3,np.nan),60)
        self.assertEqual(p.result()["return_pct"],0)
        self.assertEqual(p.result()["fills"],0)

    def test_all_registry_members_accounted_for(self):
        names={s["strategy"] for row in frozen_catalog() for s in row["config"]["members"]}
        self.assertEqual(set(REGISTRY)-names,{"lev_low","lev_medium","lev_high"})
        self.assertGreater(len(frozen_catalog()),500)

    def test_weighted_policy_cannot_trade_its_training_prefix(self):
        key=spec_id({"strategy":"buy_and_hold","params":{}})
        cfg={"mode":"weighted","members":[{"strategy":"buy_and_hold","params":{}}],"persistence":1,"weights":[1],"weighting":"inverse-absolute-correlation"}
        with np.errstate(invalid="ignore",divide="ignore"):
            _,mask=policy_signal(cfg,{key:np.ones(600)},{key:np.ones(600,dtype=bool)},np.ones(600,dtype=bool))
        self.assertFalse(mask[:256].any()); self.assertTrue(mask[256:].all())

    def test_future_gap_does_not_change_weighted_training_prefix(self):
        key=spec_id({"strategy":"buy_and_hold","params":{}})
        cfg={"mode":"weighted","members":[{"strategy":"buy_and_hold","params":{}}],"persistence":1,"weights":[1],"weighting":"inverse-absolute-correlation"}
        valid=np.ones(600,dtype=bool)
        changed=valid.copy(); changed[500]=False
        with np.errstate(invalid="ignore",divide="ignore"):
            a,ma=policy_signal(cfg,{key:np.ones(600)},{key:valid},valid)
            b,mb=policy_signal(cfg,{key:np.ones(600)},{key:valid},changed)
        np.testing.assert_equal(a[:500],b[:500])
        np.testing.assert_equal(ma[:500],mb[:500])

    def test_affordable_buy_uses_actual_quantity_depth(self):
        tape=fixture_tape()
        tape["books"][0,1,0]=[200,60]
        p=Portfolio(tape,60)
        self.assertTrue(p.target(1,0,60*NS))
        self.assertGreater(p.qty,49)
        self.assertLess(p.qty,50)
        self.assertEqual(p.rejections,{})
        self.assertGreaterEqual(p.cash,-1e-8)

    def test_rejected_synthetic_transition_does_not_change_units(self):
        p=Portfolio(fixture_tape(size=.001),60,synthetic_short=True)
        self.assertFalse(p.target(1,0,60*NS))
        self.assertEqual(p.qty,0)

    def test_small_matrix_serializes_all_artifacts_and_binds_code(self):
        from research import zec_granular as g
        tape=fixture_tape()
        info={"start_ns":0,"end_ns":243*NS,"gaps":[],"wal_sha256":"fixture"}
        row={"candidate_id":"fixture-hold","family":"canonical-single","config":{
            "members":[{"strategy":"buy_and_hold","params":{}}],"mode":"single",
            "persistence":1,"rebalance_threshold":0}}
        with tempfile.TemporaryDirectory() as d, patch.object(g,"frozen_catalog",return_value=[row]), patch.object(g,"GRID",[(1,.5)]), patch.object(g,"STEPS",{"1m":60}):
            out=Path(d)
            rows,coverage=g.run_matrix(tape,info,out,fees=(60,))
            manifest=json.loads((out/"manifest.json").read_text())
            self.assertEqual(manifest["rows"],len(rows))
            self.assertIn("research/zec_granular.py",manifest["identity"]["code"])
            self.assertIsInstance(coverage["1m"]["longest_valid_segment"],int)
            self.assertTrue((out/"results.csv").is_file())

    def test_invalid_signal_exit_bypasses_rebalance_deadband(self):
        tape=fixture_tape(prices=(100,50,50,50))
        p=spot_replay(tape,{"ts":np.array([0,60]),"step":60},np.array([.3,np.nan]),10,.25)
        self.assertGreater(p.fills[0]["position"],0)
        self.assertEqual(p.fills[1]["position"],0)
        self.assertEqual(p.fills[1]["fill_ns"],121*NS)

    def test_receipt_silence_preserves_ordered_book_but_connection_loss_resets(self):
        payloads=[(1,"a","snapshot",{"bids":[[99,100]],"asks":[[101,100]]}),
                  (1.5,"a","match",{"trade_id":1,"price":100,"size":1}),
                  (4,"a","l2update",{"changes":[["buy",99,80]]}),
                  (5,"a","connection_gap",{}),
                  (6,"b","l2update",{"changes":[["buy",99,90]]}),
                  (7,"b","snapshot",{"bids":[[98,100]],"asks":[[102,100]]})]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"wal.jsonl"
            path.write_text("".join(json.dumps({"seq":i,"received_ns":int(t*NS),"connection_id":conn,"type":kind,"raw":json.dumps(payload)})+"\n" for i,(t,conn,kind,payload) in enumerate(payloads,1)))
            tape,info=prepare_capture(path,Path(d)/"out",expected_hash=hashlib.sha256(path.read_bytes()).hexdigest(),start_ns=0,end_ns=10*NS)
            self.assertEqual(tape["quote_ns"].tolist(),[NS,4*NS,7*NS])
            self.assertEqual(tape["books"][1,0,0,1],80)
            self.assertTrue(any(x[2]=="receipt_gap" for x in info["gaps"]))

    def test_capture_hash_and_sequence_checked_before_cache_publication(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"events.jsonl"
            raw={"seq":2,"received_ns":1,"type":"connection_open","raw":"{}"}
            path.write_text(json.dumps(raw)+"\n")
            with self.assertRaisesRegex(ValueError,"sequence"):
                prepare_capture(path,Path(d)/"out",expected_hash=hashlib.sha256(path.read_bytes()).hexdigest(),start_ns=0,end_ns=10*NS)
            self.assertFalse((Path(d)/"out"/"tape.npz").exists())

    def test_volty_no_warmup_is_explicitly_unusable(self):
        tape=fixture_tape()
        bars={"ts":np.array([60,120]),"step":60,"high":np.array([101.,102.]),"low":np.array([100.,101.]),"close":np.array([100.5,101.5])}
        p,usable=volty_replay(tape,bars,np.ones(2,dtype=bool),5,.75,60)
        self.assertEqual(usable,0); self.assertEqual(p.result()["fills"],0)


if __name__ == "__main__":
    unittest.main()
