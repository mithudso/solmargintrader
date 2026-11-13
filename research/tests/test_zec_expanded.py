"""Expanded-universe coverage, causal contexts and new lifecycle accounting."""
import copy
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from research import zec_expanded as e
from research import zec_granular as g
from research import zec_lifecycle as life


def bars(n=150,step=60):
    t=np.arange(n,dtype=np.int64)*step+step
    c=100+np.sin(np.arange(n)*2*np.pi/10)+np.arange(n)*.005
    return {"ts":t,"open":c.copy(),"high":c+.2,"low":c-.2,"close":c,"volume":np.ones(n),"step":step}


def tape_for(a):
    step=a["step"]
    seconds=np.arange(0,(len(a["ts"])+3)*step,dtype=np.int64)
    price=np.interp(seconds,a["ts"]+step,a["close"],left=a["close"][0],right=a["close"][-1])
    books=np.zeros((len(seconds),2,40,2))
    books[:,0,0,0]=price-.01;books[:,1,0,0]=price+.01
    books[:,0,0,1]=books[:,1,0,1]=10000
    return {"trade_ns":seconds*g.NS,"price":price,"size":np.ones(len(seconds)),
            "quote_ns":seconds*g.NS,"books":books,"end_ns":int(seconds[-1]+1)*g.NS,"gaps":[]}


class Expanded(unittest.TestCase):
    def test_complete_catalog_has_more_than_baseline_and_keeps_census(self):
        root=Path(__file__).resolve().parents[2]
        frozen=json.loads(gzip.decompress((root/"research/zec-expanded-20261113.llms/plan.json.gz").read_bytes()))["inventory"]
        c=e.catalogue(root)
        self.assertEqual(len(c["candidates"]),1707)
        self.assertEqual(c["candidates"],frozen["candidates"])
        self.assertEqual(len(c["queue_census"]),1011)
        self.assertEqual(len(c["planning_exclusions"]),50)
        self.assertEqual(len(c["planning_exclusion_records"]),50)
        actual={row["job_id"] for row in c["queue_census"]}
        excluded={row["job_id"] for row in c["planning_exclusions"]}
        self.assertFalse(actual & excluded)
        historical_ids={row["job_id"] for row in frozen["queue_census"]}
        self.assertTrue(historical_ids <= actual | excluded)
        self.assertEqual(len(historical_ids-actual),48)
        self.assertEqual(len(excluded-historical_ids),2)
        self.assertEqual(len(c["card_census"]),1478)
        self.assertEqual(len({x["candidate_id"] for x in c["candidates"]}),1707)
        self.assertTrue(any(not x["executable"] for x in c["card_census"]))
        for row in c["candidates"]:
            for spec in row["config"]["members"]:
                self.assertFalse(spec["strategy"].startswith("lev_"))

    def test_historical_source_archive_and_original_queue_census(self):
        root=Path(__file__).resolve().parents[2]
        archive=root/"research/zec-expanded-20261113.llms"
        frozen=json.loads(gzip.decompress((archive/"plan.json.gz").read_bytes()))["inventory"]
        identity=json.loads((archive/"identity.json").read_text())["code_and_cards"]
        with zipfile.ZipFile(archive/"simulation-source.zip") as source:
            self.assertEqual(set(source.namelist()),set(identity))
            for name,digest in identity.items():
                self.assertEqual(hashlib.sha256(source.read(name)).hexdigest(),digest,name)
            with tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/"archived_bgqueue.py"
                path.write_bytes(source.read("soltui/bgqueue.py"))
                spec=importlib.util.spec_from_file_location("soltui._zec_archived_bgqueue",path)
                module=importlib.util.module_from_spec(spec)
                with patch.dict(sys.modules,{module.__name__:module}):
                    spec.loader.exec_module(module)
                    def historical_queue(*args,**kwargs):
                        kwargs.pop("exclusions",None)
                        return module.build_queue(*args,**kwargs)
                    with patch.object(e,"build_queue",side_effect=historical_queue):
                        historical=e.catalogue(root)
        self.assertEqual(len(historical["queue_census"]),1059)
        self.assertEqual(len(historical["invalid_jobs"]),46)
        self.assertEqual(sum(row["status"]=="unsupported_actual_perp_inputs" for row in historical["queue_census"]),30)
        for name in ("candidates","queue_census","invalid_jobs","card_census"):
            self.assertEqual(historical[name],frozen[name],name)

    def test_context_prefix_is_unchanged_when_future_prices_poisoned(self):
        a=bars();valid=np.ones(150,dtype=bool)
        x,fits,_=e.contexts(a,valid,60,replicates=3)
        poisoned=copy.deepcopy(a)
        for name in ("open","high","low","close"):poisoned[name][100:]*=5
        y,other,_=e.contexts(poisoned,valid,60,replicates=3)
        for name in x:np.testing.assert_equal(x[name][:100],y[name][:100])
        self.assertEqual([f for f in fits if f["decision_start"]<100],[f for f in other if f["decision_start"]<100])

    def test_frequency_requires64pastbars_and_freezes16decisions(self):
        a=bars(100);ctx,fits,_=e.contexts(a,np.ones(100,dtype=bool),60,replicates=3)
        self.assertTrue(np.isnan(ctx["cycle"][:63]).all())
        self.assertTrue(np.isfinite(ctx["cycle"][63:79]).all())
        self.assertEqual(fits[0]["decision_stop_exclusive"]-fits[0]["decision_start"],16)
        self.assertEqual(fits[0]["train_last"]+60,fits[0]["available_at"])
        self.assertEqual(fits[1]["decision_start"]-fits[0]["decision_start"],16)

    def test_gap_resets_context_history_without_future_censoring(self):
        a=bars(150);valid=np.ones(150,dtype=bool);valid[100]=False
        x,_,_=e.contexts(a,valid,60,replicates=3)
        y,_,_=e.contexts(a,np.ones(150,dtype=bool),60,replicates=3)
        np.testing.assert_equal(x["cycle"][:100],y["cycle"][:100])
        self.assertTrue(np.isnan(x["cycle"][100]))
        self.assertTrue(np.isfinite(x["cycle"][101:]).any())
        self.assertTrue((x["shape"][101:148]=="unknown").all())

    def test_irregular_frequency_fit_preserves_observed_times_and_coverage(self):
        a=bars(150);valid=np.ones(150,dtype=bool);valid[[70,105]]=False
        _,fits,_=e.contexts(a,valid,60,replicates=3)
        after=[x for x in fits if x["decision_start"]>70]
        self.assertTrue(after)
        for fit in after:
            self.assertGreaterEqual(fit["training_coverage"],.95)
            self.assertNotIn(70,fit["training_indices"])
            self.assertEqual(len(fit["training_indices"]),64)

    def test_coarse_history_insufficiency_is_explicit(self):
        ctx,fits,tests=e.contexts(bars(10,3600),np.ones(10,dtype=bool),3600,replicates=3)
        self.assertTrue((ctx["shape"]=="unknown").all())
        self.assertTrue(np.isnan(ctx["cycle"]).all());self.assertEqual(fits,[]);self.assertEqual(tests,[])

    def test_gates_have_matched_history_controls(self):
        ctx={"shape":np.array(["unknown","range","trend_up","cap"]),"cycle":np.array([np.nan,1,-1,1]),"linear":np.array([np.nan,-1,-1,-1])}
        spec={"members":[{"strategy":"macd","params":{}}]}
        np.testing.assert_equal(e.gate_for("shape_control",ctx),[np.nan,1,1,1])
        np.testing.assert_equal(e.gate_for("shape",ctx,spec),[np.nan,0,1,0])
        np.testing.assert_equal(e.gate_for("frequency_control",ctx),[np.nan,1,1,1])
        np.testing.assert_equal(e.gate_for("frequency",ctx),[np.nan,1,0,1])
        np.testing.assert_equal(e.gate_for("linear_control",ctx),[np.nan,0,0,0])

    def test_baseline_volty_matches_existing_stop_runner(self):
        a=bars(80);t=tape_for(a);valid=np.ones(80,dtype=bool)
        x,n=g.volty_replay(t,a,valid,5,.75,15)
        y,m=e.controlled_volty(t,a,valid,5,.75,15,np.ones(80),np.ones(80))
        self.assertEqual(x.fills,y.fills);self.assertEqual(x.result(),y.result());self.assertEqual(n,m)

    def test_volty_context_cannot_read_current_unclosed_bar(self):
        a=bars(80);t=tape_for(a);valid=np.ones(80,dtype=bool)
        allone=np.ones(80);changed=allone.copy();changed[50:]=0
        x,_=e.controlled_volty(t,a,valid,3,.5,15,allone,allone)
        y,_=e.controlled_volty(t,a,valid,3,.5,15,changed,changed)
        boundary=(int(a["ts"][50])+60)*g.NS+g.NS
        self.assertEqual([f for f in x.fills if f["decision_ns"]<boundary-g.NS],[f for f in y.fills if f["decision_ns"]<boundary-g.NS])

    def test_linear_control_fits_without_selected_harmonic(self):
        a=bars(80);ctx,fits,_=e.contexts(a,np.ones(80,dtype=bool),60,replicates=3)
        y=np.log(a["close"][:64]);x=np.column_stack([np.ones(64),np.arange(64)/64])
        direct=np.linalg.lstsq(x,y,rcond=None)[0]
        np.testing.assert_allclose(fits[0]["linear_coefficients"],direct)
        self.assertEqual(ctx["linear"][63],1 if direct[1]>0 else -1)

    def test_dca_safety_fill_cancels_stale_takeprofit_until_next_close(self):
        a=bars(5)
        for name in ("open","high","low","close"):a[name]=np.full(5,100.)
        t=tape_for(a)
        seconds=t["quote_ns"]//g.NS
        prices=np.where((seconds>=190)&(seconds<200),97.,np.where(seconds>=200,103.,100.))
        t["price"]=prices
        t["books"][:,0,0,0]=prices-.01;t["books"][:,1,0,0]=prices+.01
        cfg=next(x for x in life.lifecycle_configs() if x["kind"]=="dca_safety_reference" and x["params"]["take_profit_pct"]==2.)
        p,_d=life.replay_lifecycle(t,a,np.ones(5,dtype=bool),np.ones(5),cfg,15)
        safety=[f for f in p.fills if f.get("lifecycle_reason")=="dca_safety"]
        self.assertTrue(safety)
        stale=[f for f in p.fills if f.get("lifecycle_reason")=="dca_take_profit" and 200*g.NS<=f["fill_ns"]<241*g.NS]
        self.assertEqual(stale,[])
        exitfills=[f for f in p.fills if f.get("lifecycle_reason")=="dca_take_profit"]
        self.assertTrue(exitfills)
        self.assertLess(exitfills[0]["order_limit"],110.)
        self.assertGreater(-exitfills[0]["qty"],1.9)

    def test_lifecycle_configs_are20finite_valid_cases(self):
        cfg=life.lifecycle_configs();self.assertEqual(len(cfg),20)
        self.assertEqual(sum(x["kind"]=="ladder_grid_reference" for x in cfg),8)
        self.assertEqual(sum(x["kind"]=="dca_safety_reference" for x in cfg),12)

    def test_contexts_are_unchanged_by_future_gap_at_final_valid_close(self):
        a=bars(130);valid=np.ones(130,dtype=bool);changed=valid.copy();changed[100]=False
        first,_,_=e.contexts(a,valid,60,replicates=3)
        second,_,_=e.contexts(a,changed,60,replicates=3)
        self.assertTrue(np.isfinite(second["cycle"][99]))
        np.testing.assert_equal(first["cycle"][:100],second["cycle"][:100])

    def test_parent_manifest_binding_refuses_unaccepted_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"manifest.json").write_text("{}")
            with self.assertRaisesRegex(ValueError,"accepted shared archive"):
                e.input_identity(p)

    def test_affordable_limit_quote_uses_cash_and_fee(self):
        a=bars(5);t=tape_for(a);p=g.Portfolio(t,25,capital=100)
        units,price=life.affordable_quote(p,0,"buy",10000)
        self.assertLess(units,1);self.assertAlmostEqual(units*price*(1+.0025),100)

    def test_dca_fee_cash_and_terminal_flatness(self):
        a=bars(90);t=tape_for(a);cfg=next(x for x in life.lifecycle_configs() if x["kind"]=="dca_safety_reference")
        p,details=life.replay_lifecycle(t,a,np.ones(90,dtype=bool),np.ones(90),cfg,25)
        self.assertGreater(len(p.fills),0);self.assertLess(abs(p.qty),1e-8)
        self.assertAlmostEqual(p.fees,p.turnover*.0025)
        self.assertGreaterEqual(p.cash,-1e-8);self.assertGreater(details["eligible_bars"],0)
        for f in p.fills:
            self.assertGreaterEqual(f["fill_ns"]-f["decision_ns"],g.NS)
            if f.get("order_limit") is not None:
                self.assertLessEqual(f["price"],f["order_limit"]) if f["qty"]>0 else self.assertGreaterEqual(f["price"],f["order_limit"])

    def test_grid_never_places_from_future_training_range(self):
        a=bars(90);t=tape_for(a);cfg=life.lifecycle_configs()[0]
        p,_=life.replay_lifecycle(t,a,np.ones(90,dtype=bool),np.ones(90),cfg,15)
        earliest=(int(a["ts"][47])+60)*g.NS
        self.assertTrue(all(f["decision_ns"]>=earliest for f in p.fills))
        self.assertLess(abs(p.qty),1e-8)

    def test_lifecycle_future_price_poison_does_not_change_old_fills(self):
        a=bars(90);t=tape_for(a);other=copy.deepcopy(a)
        for name in ("open","high","low","close"):other[name][60:]*=2
        t2=tape_for(other);cfg=next(x for x in life.lifecycle_configs() if x["kind"]=="dca_safety_reference")
        p,_=life.replay_lifecycle(t,a,np.ones(90,dtype=bool),np.ones(90),cfg,15)
        q,_=life.replay_lifecycle(t2,other,np.ones(90,dtype=bool),np.ones(90),cfg,15)
        # Interpolated fixture trade/book prices change from timestamp60 onward;
        # compare before that first changed observable input.
        cutoff=int(a["ts"][59]+60)*g.NS
        self.assertEqual([f for f in p.fills if f["fill_ns"]<cutoff],[f for f in q.fills if f["fill_ns"]<cutoff])

    def test_all_contexts_disabled_means_no_invented_dca_trades(self):
        a=bars(30);t=tape_for(a);cfg=life.lifecycle_configs()[-1]
        p,d=life.replay_lifecycle(t,a,np.ones(30,dtype=bool),np.full(30,np.nan),cfg,15)
        self.assertEqual(len(p.fills),0);self.assertEqual(d["eligible_bars"],0)

    def test_small_full_matrix_serializes_final_artifacts(self):
        a=bars(80);t=tape_for(a);info={"wal_sha256":g.CAPTURE_HASH,"tape_sha256":"mock","start_ns":0,"end_ns":int(t["end_ns"]),"gaps":[]}
        row={"candidate_id":"fixture","family":"test","config":{"members":[{"strategy":"buy_and_hold","params":{}}],"mode":"single","persistence":1,"rebalance_threshold":0},"provenance":[]}
        inv={"candidates":[row],"registry":["buy_and_hold"],"card_census":[],"queue_census":[],"invalid_jobs":[],"special_runners":{}}
        with tempfile.TemporaryDirectory() as d,patch.object(e,"catalogue",return_value=inv),patch.object(e,"identity",return_value={"test":True}),patch.object(e,"input_identity",return_value={"fixture":True}),patch.object(g,"digest",return_value="mock"),patch.object(g,"make_bars",return_value=(a,np.ones(80,dtype=bool),np.ones(80,dtype=int))),patch.object(g,"STEPS",{"1m":60}),patch.object(g,"GRID",[(2,.5)]),patch.object(life,"lifecycle_configs",return_value=[]):
            root=Path(d);parent=root/"parent";parent.mkdir();g.save_json(parent/"capture.json",info)
            np.savez(parent/"tape.npz",**{k:v for k,v in t.items() if k not in {"gaps","end_ns"}})
            rows,_=e.run(parent,root/"out",replicates=3)
            self.assertEqual(len(rows),28)
            self.assertTrue((root/"out/manifest.json").is_file())
            self.assertTrue((root/"out/results.csv").is_file())
            self.assertTrue((root/"out/cycle-null-tests.json").is_file())


if __name__=="__main__":unittest.main()
