"""Expanded offline ZEC strategy, causal shape and frozen-frequency comparisons.

All policies are reference simulations; no network, signing or order path exists.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.strategies import REGISTRY, build
from backtester.core.strategy_cards import load_all, load_card
from backtester.core.zec_ensemble import spec_id
from research import zec_granular as g
from research.shape_study import detect_shapes
from research.zec_cycles import Spectrum, holm, null_test
from soltui.bgqueue import build_queue

FEES = (25, 15)
MODES = ("baseline", "shape", "shape_control", "frequency", "frequency_control", "linear_control")
TRAIN = 64
BLOCK = 16
SEED = 20261113
SHAPE_RULE = {
    "trend": ["trend_up", "bowl"],
    "breakout": ["compression", "trend_up"],
    "reversion": ["range", "v_rebound", "bowl"],
    "general": ["range", "trend_up", "v_rebound", "bowl", "compression"],
}


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()[:24]


def normalize_spec(spec):
    kind = spec["strategy"]
    return {"strategy": kind, "params": dict(build(kind, **spec.get("params", {})).params)}


def catalogue(root: Path):
    """Finite published queue, preserving every source row before deduplication."""
    cards = load_all(root/"backtester/strategy_cards")
    census, jobs, invalid = [], [], []
    for path in sorted((root/"backtester/strategy_cards").rglob("*.md")):
        record = {"path": str(path.relative_to(root)), "sha256": g.digest(path)}
        if path.name.upper().startswith("README"):
            record.update(status="navigation", executable=False)
        else:
            try:
                card = load_card(path)
                record.update(status=card.status, executable=card.implemented,
                              registry_key=card.registry_key, runner=card.runner, kind=card.kind)
            except ValueError as exc:
                # Publication/profile documents have a different metadata schema;
                # record the actual parse reason rather than inventing an entry.
                record.update(status="profile_document_without_registry_entry", executable=False,
                              reason=f"{type(exc).__name__}: {exc}")
        census.append(record)
    rows = {}

    def add(config, family, provenance):
        cfg = copy.deepcopy(config)
        for field in ("members",):
            cfg[field] = [normalize_spec(s) for s in cfg[field]]
        for field in ("gate", "fallback"):
            if field in cfg:
                cfg[field] = normalize_spec(cfg[field])
        cfg.pop("interval", None)
        cfg.pop("schema_version", None)
        cfg.setdefault("persistence", 1)
        cfg.setdefault("rebalance_threshold", 0.0)
        cid = key(cfg)
        if cid not in rows:
            rows[cid] = {"candidate_id": cid, "family": family, "config": cfg, "provenance": []}
        rows[cid]["provenance"].append(provenance)

    for row in g.frozen_catalog():
        add(row["config"], "existing-ensemble-catalog", {"prior_template_id": row["candidate_id"]})
    planning_exclusions = []
    queue = build_queue("ZEC", cards=cards, max_tier=2, exclusions=planning_exclusions)
    exclusion_records = [item.to_dict() for item in planning_exclusions]
    unique_exclusions = {item["job_id"]: item for item in exclusion_records}
    for job in queue:
        record = {"job_id": job.job_id, "strategy": job.strategy, "params": dict(job.params),
                  "horizon": job.horizon, "variation": job.variation, "tier": job.tier}
        if job.strategy.startswith("lev_"):
            record.update(status="unsupported_actual_perp_inputs", reason="spot tape has no venue funding/liquidation oracle")
        else:
            try:
                add({"members": [{"strategy": job.strategy, "params": dict(job.params)}],
                     "mode": "single"}, "card-preset-parameter-perturbation", record)
                record["status"] = "executable"
            except (ValueError, TypeError, KeyError) as exc:
                record.update(status="invalid_declared_parameter_combination", reason=str(exc))
                invalid.append(record)
        jobs.append(record)
    return {"candidates": list(rows.values()), "card_census": census, "queue_census": jobs,
            "invalid_jobs": invalid,
            "planning_exclusions": list(unique_exclusions.values()),
            "planning_exclusion_records": exclusion_records,
            "registry": sorted(REGISTRY),
            "special_runners": {"grid": "new event lifecycle reference adapter", "dca_safety": "new event lifecycle reference adapter",
                                "volty": "observed-stop synthetic1x margin reference adapter",
                                "triangle": "unsupported: other two legs absent",
                                "pairs": "unsupported: second instrument absent",
                                "compound": "unsupported: complete BTC/context and venue execution absent"}}


def identity():
    root = Path(__file__).resolve().parents[1]
    paths = [Path(__file__), root/"research/zec_lifecycle.py", root/"research/zec_granular.py",
             root/"research/zec_ensembles.py", root/"research/shape_study.py", root/"research/zec_cycles.py",
             root/"soltui/bgqueue.py", *sorted((root/"backtester/core").rglob("*.py")), root/"backtester/voltycli.py"]
    paths += sorted((root/"backtester/strategy_cards").rglob("*.md"))
    return {"code_and_cards": {str(p.relative_to(root)): g.digest(p) for p in paths},
            "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "executable": sys.executable}


def contexts(bars, valid, step, replicates=4999):
    """Feature times are bar-close times. Fits never read their evaluation block."""
    n = len(valid)
    shape = np.full(n, "unknown", dtype="U16")
    zone = np.full(n, "unknown", dtype="U16")
    position = np.full(n, np.nan)
    cycle = np.full(n, np.nan)
    linear = np.full(n, np.nan)
    fits, tests = [], []
    for a, b in g.segments(valid):
        frame = pd.DataFrame({"timestamp": bars["ts"][a:b], **{k: bars[k][a:b] for k in ("open", "high", "low", "close", "volume")}})
        if b-a >= 48:
            tags = detect_shapes(frame, window=48)
            shape[a:b], zone[a:b] = tags["shape"], tags["zone"]
            position[a:b] = tags["range_position"]
    # The prior cycle study permits irregular timestamps at >=95% coverage.
    # This is distinct from indicator/shape state, which still resets at gaps.
    frame=pd.DataFrame({"timestamp":bars["ts"],"close":bars["close"]})
    observed=np.flatnonzero(valid)
    for decision in range(TRAIN-1, n, BLOCK):
        if not valid[decision]:
            continue
        past=observed[observed<=decision][-TRAIN:]
        if len(past)<TRAIN:
            continue
        expected=(int(bars["ts"][past[-1]])-int(bars["ts"][past[0]]))/step+1
        training_coverage=TRAIN/expected
        if training_coverage<.95:
            continue
        train=frame.iloc[past]
        ts, y = train.timestamp.to_numpy(float), np.log(train.close.to_numpy(float))
        projector = Spectrum(ts, step)
        power = projector.power(y)[0]
        period = float(projector.periods[int(np.argmax(power))])
        scale = ts[-1]-ts[0]+step

        def design(times, harmonic=True, ts=ts, scale=scale, period=period):
            elapsed = np.asarray(times)-ts[0]
            x = [np.ones(len(elapsed)), elapsed/scale]
            if harmonic:
                x += [np.cos(2*np.pi*elapsed/period), np.sin(2*np.pi*elapsed/period)]
            return np.column_stack(x)

        coef = np.linalg.lstsq(design(ts), y, rcond=None)[0]
        linear_coef = np.linalg.lstsq(design(ts, False), y, rcond=None)[0]
        stop = min(n, decision+BLOCK)
        now = bars["ts"][decision:stop]
        # Remove the separately fitted linear term: this gate tests the
        # frozen harmonic increment, not an unsigned trend extrapolation.
        increment = (design(now+step)-design(now))[:, 2:] @ coef[2:]
        cycle[decision:stop] = np.where(valid[decision:stop], np.where(increment > 0, 1.0, -1.0), np.nan)
        linear[decision:stop] = np.where(valid[decision:stop], 1.0 if linear_coef[1] > 0 else -1.0, np.nan)
        frozen = {"train_first": int(ts[0]), "train_last": int(ts[-1]),
                  "available_at": int(bars["ts"][decision]+step), "decision_start": int(decision),
                  "decision_stop_exclusive": int(stop), "period_seconds": period,
                  "training_indices": past.tolist(), "training_coverage": float(training_coverage),
                  "power": float(power.max()), "coefficients": coef.tolist(), "linear_coefficients": linear_coef.tolist(), "scale": float(scale)}
        fits.append(frozen)
        rows, _, _, _ = null_test(ts, y, step, replicates=replicates,
                               seed=SEED+int(decision)+step)
        for row in rows:
            tests.append({**row, "interval_seconds": step, "fit_available_at": frozen["available_at"],
                          "train_start": int(ts[0]), "train_end": int(ts[-1])})
    return {"shape": shape, "zone": zone, "range_position": position,
            "cycle": cycle, "linear": linear}, fits, tests


def family(config):
    kinds = {s["strategy"] for s in config["members"]}
    if kinds <= {"rsi", "bb_reversion", "zscore", "vwap_reversion", "ou_reversion", "stochastic"}:
        return "reversion"
    if kinds <= {"breakout", "bb_breakout", "keltner"}:
        return "breakout"
    if kinds <= {"macd", "ppo", "ema_crossover", "ma_crossover", "obv_trend", "ts_momentum", "adx_trend", "ma_ribbon", "swing_confluence", "dual_momentum", "sma_regime", "ichimoku"}:
        return "trend"
    return "general"


def gate_for(mode, ctx, config=None, *, direction=1):
    n = len(ctx["shape"])
    if mode == "baseline":
        return np.ones(n)
    if mode in {"shape", "shape_control"}:
        known = ctx["shape"] != "unknown"
        if mode == "shape_control":
            return np.where(known, 1., np.nan)
        allowed = SHAPE_RULE[family(config)] if config is not None else SHAPE_RULE["general"]
        if direction < 0:
            mirror = {"trend_up":"trend_down", "bowl":"cap", "v_rebound":"inverted_v"}
            allowed = [mirror.get(x,x) for x in allowed]
        return np.where(known, np.isin(ctx["shape"], allowed).astype(float), np.nan)
    known = np.isfinite(ctx["cycle"])
    if mode == "frequency_control":
        return np.where(known, 1., np.nan)
    values = ctx["linear"] if mode == "linear_control" else ctx["cycle"]
    return np.where(known, (values*direction > 0).astype(float), np.nan)


def controlled_volty(tape, bars, valid, length, mult, fee, allow_long, allow_short):
    """Same observed-stop model as baseline; gates use only the previous close."""
    levels = [np.full(len(valid)+1, np.nan), np.full(len(valid)+1, np.nan)]
    for a,b in g.segments(valid):
        arrays = {k:np.r_[bars[k][a:b], bars[k][b-1]] for k in ("high","low","close")}
        upper,lower = g.stop_levels(arrays,g.VoltyConfig(length=length,atr_mult=mult))
        levels[0][a:b+1],levels[1][a:b+1] = upper,lower
    p = g.Portfolio(tape,fee,synthetic_short=True)
    desired,pending = 0,None
    gaps = sorted(x[1] for x in tape["gaps"])
    gap_i,invalid_until = 0,-1
    usable = np.zeros(len(valid),dtype=bool)
    step=int(bars["step"])
    for t,price in zip(tape["trade_ns"],tape["price"]):
        t=int(t)
        if t >= int(tape["end_ns"])-3*g.NS:
            break
        while gap_i<len(gaps) and gaps[gap_i]<=t:
            invalid_until=(gaps[gap_i]//(step*g.NS)+1)*step*g.NS
            gap_i+=1
        if pending is not None and int(tape["quote_ns"][pending[0]])<=t:
            if p.target(pending[1],pending[0],pending[2]):
                desired=pending[1]
            pending=None
        bar=(t//g.NS-int(bars["ts"][0]))//step
        if not 0<=bar<len(valid) or t<(int(bars["ts"][bar])+1)*g.NS:
            continue
        up,down=levels[0][bar],levels[1][bar]
        # Current-bar labels are unavailable. A context computed at previous
        # close becomes eligible one second into this bar.
        long_ok=bar>0 and np.isfinite(allow_long[bar-1]) and allow_long[bar-1]>0
        short_ok=bar>0 and np.isfinite(allow_short[bar-1]) and allow_short[bar-1]>0
        if np.isfinite(up) and bar>0 and (np.isfinite(allow_long[bar-1]) or np.isfinite(allow_short[bar-1])):
            usable[bar]=True
        target=0 if not np.isfinite(up) or t<invalid_until else (1 if price>=up else (-1 if price<=down else desired))
        if (target>0 and not long_ok) or (target<0 and not short_ok):
            target=0
        if pending is None and target!=desired:
            i=p.quote_index(t+g.LATENCY_NS)
            if i is None:
                p.rejections["no_fresh_book"]+=1
            else:
                pending=(i,target,t)
    if pending is not None and int(tape["quote_ns"][pending[0]])<int(tape["end_ns"])-2*g.NS:
        p.target(pending[1],pending[0],pending[2])
    g.terminal_close(p)
    return p,int(usable.sum())


def input_identity(parent):
    root=Path(__file__).resolve().parents[1]
    pinned=root/"research/zec-granular-20261113.llms/manifest.json"
    manifest=parent/"manifest.json"
    if g.digest(manifest)!=g.digest(pinned):
        raise ValueError("parent manifest differs from accepted shared archive")
    prior=json.loads(manifest.read_text())
    hashes={"manifest.json":g.digest(manifest)}
    for name in ("capture.json","tape.npz"):
        hashes[name]=g.digest(parent/name)
        if hashes[name]!=prior["artifacts"][name]:
            raise ValueError("parent input differs from accepted manifest: "+name)
    info=json.loads((parent/"capture.json").read_text())
    if info["wal_sha256"]!=g.CAPTURE_HASH or info["tape_sha256"]!=hashes["tape.npz"]:
        raise ValueError("captured source binding mismatch")
    return {"parent":str(parent.resolve()),"accepted_manifest":str(pinned),"hashes":hashes,
            "wal_sha256":info["wal_sha256"],"prior_run":"run:55f2cb71690fb0115c42324012967ff835eb3137e4a7f3cd6a80522a335123d0"}


def run(parent, output, replicates=4999):
    from research.zec_lifecycle import lifecycle_configs, replay_lifecycle

    output.mkdir(parents=True,exist_ok=True)
    import fcntl
    with (output/"run.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (output/"manifest.json").exists():
            raise ValueError("finished output is immutable")
        frozen=identity()
        input_proof=input_identity(parent)
        g.save_json(output/"input-provenance.json",input_proof)
        info=json.loads((parent/"capture.json").read_text())
        if info["wal_sha256"]!=g.CAPTURE_HASH or g.digest(parent/"tape.npz")!=info["tape_sha256"]:
            raise ValueError("original prepared tape hash mismatch")
        with np.load(parent/"tape.npz",allow_pickle=False) as source:
            tape={k:source[k] for k in source.files}
        tape["end_ns"],tape["gaps"]=info["end_ns"],info["gaps"]
        inventory=catalogue(Path(__file__).resolve().parents[1])
        plan={"version":"1.0.0","inventory":inventory,"fee_bps":FEES,"modes":MODES,"steps":g.STEPS,
              "shape_rule":SHAPE_RULE,"shape_window":48,"frequency_train":TRAIN,"frequency_block":BLOCK,"frequency_min_training_coverage":.95,
              "null_replicates_per_model":replicates,"seed":SEED,"lifecycle_configs":lifecycle_configs(),
              "source_sha256":info["wal_sha256"],"selection":"predeclared complete finite universe; no post-result tuning",
              "execution":"crossing-book reference with latency/depth/costs; limit-trigger lifecycle is separate reference model"}
        g.save_json(output/"plan.json",plan)
        g.save_json(output/"identity.json",frozen)
        rows,coverage,all_tests=[],{},[]
        artifacts=[]
        with gzip.open(output/"fills.jsonl.gz","wt") as fills:
            for interval,step in g.STEPS.items():
                bars,valid,counts=g.make_bars(tape,info,step)
                bars["step"]=step
                np.savez(output/f"bars-{interval}.npz",**bars,valid=valid,trades=counts)
                ctx,fits,tests=contexts(bars,valid,step,replicates)
                all_tests+=tests
                np.savez(output/f"contexts-{interval}.npz",**ctx)
                g.save_json(output/f"frequency-fits-{interval}.json",fits)
                coverage[interval]={"complete_bars":len(valid),"valid_bars":int(valid.sum()),
                                    "shape_known":int(np.sum(ctx["shape"]!="unknown")),
                                    "frequency_known":int(np.isfinite(ctx["cycle"]).sum()),
                                    "shape_counts":dict(Counter(ctx["shape"].tolist())),"frequency_fits":len(fits)}
                specs={}
                for row in inventory["candidates"]:
                    cfg=row["config"]
                    for spec in [*cfg["members"],*([cfg["gate"]] if "gate" in cfg else []),*([cfg["fallback"]] if "fallback" in cfg else [])]:
                        specs[spec_id(spec)]=spec
                signals,eligible={},{}
                for number,(sid,spec) in enumerate(specs.items(),1):
                    signals[sid],eligible[sid]=g.member_signals(spec,bars,valid,step)
                    if number%100==0:
                        print(f"{interval}:member{number}/{len(specs)}",flush=True)
                cache={}

                def record(p,base,replay_id,cache=cache):
                    result=p.result()
                    cache[replay_id]=result
                    for f in p.fills:
                        fills.write(json.dumps({"replay_id":replay_id,**f},allow_nan=False)+"\n")
                    return result

                for number,candidate in enumerate(inventory["candidates"],1):
                    cfg=candidate["config"]
                    raw,mask=g.policy_signal(cfg,signals,eligible,valid)
                    for mode in MODES:
                        allow=gate_for(mode,ctx,cfg)
                        values=raw*allow
                        available=mask & np.isfinite(allow)
                        for fee in FEES:
                            base={"interval":interval,"candidate_id":candidate["candidate_id"],"family":candidate["family"],
                                  "mode":mode,"fee_bps":fee,"market":"spot_reference","eligible_bars":int(available.sum())}
                            if not available.any():
                                rows.append({**base,"status":"insufficient_contiguous_history"})
                                continue
                            payload=np.nan_to_num(values,nan=-1.).astype("<f8").tobytes()
                            replay_id=hashlib.sha256(interval.encode()+str(fee).encode()+str(cfg["rebalance_threshold"]).encode()+payload).hexdigest()[:24]
                            if replay_id not in cache:
                                p=g.spot_replay(tape,bars,values,fee,cfg["rebalance_threshold"])
                                record(p,base,replay_id)
                            rows.append({**base,"status":"completed", "replay_id":replay_id,**cache[replay_id]})
                    if number%200==0:
                        print(f"{interval}:policy{number}/{len(inventory['candidates'])},rows{len(rows)},unique_replays{len(cache)}",flush=True)
                for length,mult in g.GRID:
                    for mode in MODES:
                        long,short=gate_for(mode,ctx),gate_for(mode,ctx,direction=-1)
                        for fee in FEES:
                            if mode=="baseline":
                                p,usable=g.volty_replay(tape,bars,valid,length,mult,fee)
                            else:
                                p,usable=controlled_volty(tape,bars,valid,length,mult,fee,long,short)
                            base={"interval":interval,"candidate_id":f"volty-{length}-{mult}","family":"volty-stop",
                                  "mode":mode,"fee_bps":fee,"market":"synthetic1x_long_short","eligible_bars":usable}
                            rid=key(base)
                            result=record(p,base,rid)
                            rows.append({**base,"status":"completed" if usable else "insufficient_contiguous_history","replay_id":rid,**result})
                for cfg in lifecycle_configs():
                    for mode in MODES:
                        allow=gate_for(mode,ctx)
                        for fee in FEES:
                            p,details=replay_lifecycle(tape,bars,valid,allow,cfg,fee)
                            base={"interval":interval,"candidate_id":key(cfg),"family":cfg["kind"],"mode":mode,
                                  "fee_bps":fee,"market":"observed_cross_limit_guard_reference","eligible_bars":details["eligible_bars"]}
                            rid=key(base)
                            result=record(p,base,rid)
                            rows.append({**base,"status":"completed" if details["eligible_bars"] else "insufficient_contiguous_history", "replay_id":rid,**details,**result})
                # Same-clock cash and passive/control comparisons already exist per
                # strategy through shape_control/frequency_control/linear_control.
                for fee in FEES:
                    for name in ("cash","capture_buy_and_hold"):
                        p=g.Portfolio(tape,fee)
                        if name!="cash":
                            q=p.quote_index(info["start_ns"]+g.NS)
                            if q is not None:p.target(1,q,info["start_ns"])
                            g.terminal_close(p)
                        base={"interval":interval,"candidate_id":name,"family":"benchmark","mode":"baseline","fee_bps":fee,"market":"spot_reference"}
                        rid=key(base);result=record(p,base,rid)
                        rows.append({**base,"status":"completed","replay_id":rid,**result})
                print(f"{interval}:finished rows{len(rows)}",flush=True)
        for row in rows:
            if row["status"]=="completed" and row.get("terminal_state")=="open_unliquidated":
                row["status"]="incomplete_terminal_exit"
        if all_tests:
            corrected=holm([r["p_conservative"] for r in all_tests])
            for row,pvalue in zip(all_tests,corrected):row["p_holm_reporting_only"]=float(pvalue)
        g.save_json(output/"cycle-null-tests.json",all_tests)
        g.save_json(output/"coverage.json",coverage)
        with gzip.open(output/"results.json.gz","wt") as stream:json.dump(rows,stream,allow_nan=False)
        columns=list(dict.fromkeys(k for row in rows for k in row))
        with (output/"results.csv").open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(rows)
        if identity()!=frozen:raise ValueError("source/cards/runtime changed during run")
        if input_identity(parent)!=input_proof:raise ValueError("parent inputs changed during run")
        for path in sorted(output.iterdir()):
            if path.is_file() and path.name not in {"manifest.json","run.lock"} and path.suffix!=".log":
                artifacts.append({"name":path.name,"sha256":g.digest(path),"bytes":path.stat().st_size})
        g.save_json(output/"manifest.json",{"version":"1.0.0","rows":len(rows),"status_counts":dict(Counter(r["status"] for r in rows)),"artifacts":artifacts,"source_sha256":info["wal_sha256"],"identity":frozen})
        return rows,coverage

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parent",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--replicates",type=int,default=4999)
    ap.add_argument("--plan",action="store_true")
    args=ap.parse_args()
    if args.plan:
        value=catalogue(Path(__file__).resolve().parents[1])
        excluded=len(value["planning_exclusions"])
        print(json.dumps({"candidates":len(value["candidates"]),"cards":len(value["card_census"]),
                          "queue_jobs":len(value["queue_census"]),"planning_exclusions":excluded,
                          "planning_exclusion_records":len(value["planning_exclusion_records"]),
                          "invalid_jobs":len(value["invalid_jobs"])},indent=2))
        return
    if args.replicates<99:raise ValueError("at least99 null replicates required")
    run(args.parent,args.output,args.replicates)


if __name__=="__main__":main()
