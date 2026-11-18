"""Observed-cross, limit-guarded grid/DCA reference lifecycles, simulation only.

These use canonical ladder/deal planners. A historical trade crossing triggers a
single-flight simulated intent. After >=1s a fresh displayed book must satisfy
its exchange-price limit after adverse execution slippage; fees are separate. This is not passive queue/maker execution or the canonical
OHLC fill loop, and it deliberately does not modify those existing economics.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict

import numpy as np

from backtester.core.dcasim import DcaConfig, safety_deviations_pct, safety_sizes_usd
from backtester.core.gridsim import GridConfig, Lot, _plan, grid_levels
from research import zec_granular as g


def lifecycle_configs():
    configs=[]
    for rungs in (5,9):
        for spacing in ("geom","arith"):
            for band in ("training_range","five_percent"):
                configs.append({"kind":"ladder_grid_reference","rungs":rungs,"spacing":spacing,"band":band,
                                "warmup":48,"capital":10000,"deadband_bps":25})
    for usd in (100,1000):
        for count in (3,5):
            for tp in (1.,2.,4.):
                cfg=DcaConfig(base_order_usd=usd,safety_order_usd=usd,max_safety_orders=count,take_profit_pct=tp)
                configs.append({"kind":"dca_safety_reference","params":asdict(cfg),"capital":10000})
    return configs


def affordable_quote(p, i, side, requested):
    """Apply displayed capacity and final cash budget before checking a limit."""
    direction=1 if side=="buy" else -1
    remaining=min(requested,p.qty) if direction<0 else requested
    if remaining<=1e-10:
        return None
    budget=max(0.,p.cash) if direction>0 else float("inf")
    units=notional=0.
    for price,size in p.tape["books"][i,1 if direction>0 else 0]:
        if price<=0 or size<=0:
            continue
        cost=price*(1+direction*2/10000)*(1+p.fee)
        use=min(remaining,size,budget/cost)
        units+=use;notional+=use*price;remaining-=use;budget-=use*cost
        if remaining<1e-10 or budget<1e-8:
            break
    if units<=1e-10 or (remaining>1e-8 and budget>1e-8):
        return None
    return units,notional/units*(1+direction*2/10000)


def replay_lifecycle(tape,bars,valid,allow,config,fee):
    p=g.Portfolio(tape,fee)
    step=int(bars["step"])
    is_grid=config["kind"]=="ladder_grid_reference"
    dca=None if is_grid else DcaConfig(**config["params"])
    controls=[(int(t)+step)*g.NS+g.NS for t in bars["ts"]]
    gaps=sorted(x[1] for x in tape["gaps"])
    ci=gi=0
    orders=[]
    pending=None
    lots=[]
    grid_cfg=levels=None
    segment_start=None
    last_valid=-2
    base_price=None
    deal_notional=0.
    safety_filled=set()
    seen=Counter()
    eligible=0
    stop_time=int(tape["end_ns"])-3*g.NS

    def schedule(order, decision, *, emergency=False):
        nonlocal pending
        if pending is not None:
            return
        requested=int(decision)+g.LATENCY_NS
        i=p.quote_index(requested)
        if i is None and emergency:
            i=int(np.searchsorted(tape["quote_ns"],requested))
            if i>=len(tape["quote_ns"]):i=None
        if i is None or int(tape["quote_ns"][i])>=stop_time:
            seen["no_fresh_book"]+=1
            return
        pending={**order,"decision_ns":int(decision),"quote_index":i,
                 "fill_ns":int(tape["quote_ns"][i])}

    def reset_flat_state(reseed=False):
        nonlocal base_price,deal_notional,grid_cfg,levels,orders
        if abs(p.qty)<1e-8:
            base_price=None;deal_notional=0.;safety_filled.clear();lots.clear()
            if not is_grid:
                orders=[]
            if reseed:
                grid_cfg=levels=None

    def flatten(decision,reason):
        nonlocal orders,pending
        orders=[];pending=None
        if p.qty>1e-8:
            schedule({"side":"sell","qty":p.qty,"limit":None,"reason":reason},decision,emergency=True)
        else:
            reset_flat_state(reseed=True)

    def execute(order):
        nonlocal base_price,deal_notional,orders
        i=order["quote_index"]
        estimate=affordable_quote(p,i,order["side"],order["qty"])
        if estimate is None:
            seen["insufficient_depth_or_budget"]+=1
            return
        units,price=estimate
        limit=order.get("limit")
        if limit is not None and ((order["side"]=="buy" and price>limit) or (order["side"]=="sell" and price<limit)):
            seen["limit_not_executable_after_latency"]+=1
            return
        mid=(tape["books"][i,0,0,0]+tape["books"][i,1,0,0])/2
        delta=units if order["side"]=="buy" else -units
        target=(p.qty+delta)*mid/p.mark(i)
        before=len(p.fills)
        previous_qty=p.qty
        if not p.target(target,i,order["decision_ns"]) or len(p.fills)==before:
            seen["fill_rejected"]+=1
            return
        fill=p.fills[-1]
        fill.update(lifecycle_reason=order["reason"],order_limit=limit,requested_units=float(order["qty"]))
        if fill["qty"]>0:
            if is_grid:
                lots.append(Lot(qty=fill["qty"],price=fill["price"],level=order["entry_level"],
                                entry_fee_usd=fill["fee"],entry_slippage_usd=0,
                                opened_index=order.get("bar_index",0),opened_ts=fill["fill_ns"]//g.NS))
            else:
                if base_price is None:base_price=fill["price"]
                deal_notional+=fill["qty"]*fill["price"]
                # Like the canonical DCA loop, a buy invalidates the old TP.
                # Only a later completed-bar replan can exit the new full deal.
                orders=[o for o in orders if o["side"]!="sell"]
                if "safety_index" in order:safety_filled.add(order["safety_index"])
        elif is_grid:
            remain=-fill["qty"]
            # Preserve canonical paired-rung matching before FIFO fallback.
            wanted=order.get("closes",())
            sequence=[]
            for level,_ in wanted:
                sequence.extend(lot for lot in lots if lot.level==level and lot not in sequence)
            sequence.extend(lot for lot in lots if lot not in sequence)
            for lot in sequence:
                take=min(lot.qty,remain);lot.qty-=take;remain-=take
                if remain<1e-8:break
            lots[:]=[lot for lot in lots if lot.qty>1e-8]
        else:
            deal_notional *= max(0.,p.qty)/previous_qty if previous_qty>0 else 0.
            seen["deals_closed"]+=int(abs(p.qty)<1e-8)
        reset_flat_state(reseed=order["reason"] in {"invalid_bar_exit","context_risk_off","observed_gap_exit"})

    def control(i):
        nonlocal orders,grid_cfg,levels,segment_start,last_valid,eligible
        decision=int(bars["ts"][i]+step)*g.NS
        if not valid[i]:
            last_valid=-2;segment_start=None
            flatten(decision,"invalid_bar_exit")
            return
        if last_valid!=i-1:segment_start=i
        last_valid=i
        if not np.isfinite(allow[i]) or allow[i]<=0:
            flatten(decision,"context_risk_off")
            return
        if is_grid and i-segment_start+1<48:
            return
        eligible+=1
        if pending is not None:
            return
        close=float(bars["close"][i])
        if is_grid:
            if grid_cfg is None:
                if lots:return
                if config["band"]=="training_range":
                    lower=float(np.min(bars["low"][i-47:i+1]));upper=float(np.max(bars["high"][i-47:i+1]))
                else:
                    lower,upper=close*.95,close*1.05
                if not upper>lower:return
                grid_cfg=GridConfig(lower=lower,upper=upper,rungs=config["rungs"],spacing=config["spacing"],
                                    notional_per_rung_usd=10000/(config["rungs"]*1.1),deadband_bps=config["deadband_bps"])
                levels=grid_levels(grid_cfg)
            planned=_plan(grid_cfg,levels,close,lots,seen)
            orders=[{"side":o.side,"qty":o.qty,"limit":o.level,"entry_level":o.level,
                     "closes":o.closes,"reason":"grid_cross","bar_index":i} for o in planned]
        elif p.qty<1e-8:
            schedule({"side":"buy","qty":dca.base_order_usd/close,"limit":None,"reason":"dca_base","bar_index":i},decision)
        elif base_price is not None:
            avg=deal_notional/p.qty
            orders=[{"side":"sell","qty":p.qty,"limit":avg*(1+dca.take_profit_pct/100),"reason":"dca_take_profit","bar_index":i}]
            for k,(dev,usd) in enumerate(zip(safety_deviations_pct(dca),safety_sizes_usd(dca))):
                level=base_price*(1-dev/100)
                if k not in safety_filled:
                    orders.append({"side":"buy","qty":usd/level,"limit":level,"reason":"dca_safety","safety_index":k,"bar_index":i})
        # Orders only become observable/eligible one second after this close.

    def drain(until):
        nonlocal ci,gi,pending,orders,last_valid,segment_start
        while True:
            options=[]
            if ci<len(controls):options.append((controls[ci],2,"control"))
            if gi<len(gaps):options.append((gaps[gi],0,"gap"))
            if pending is not None:options.append((pending["fill_ns"],1,"fill"))
            if not options:return
            when,_,kind=min(options)
            if when>until or when>=stop_time:return
            if kind=="gap":
                gi+=1;last_valid=-2;segment_start=None
                flatten(when,"observed_gap_exit")
            elif kind=="fill":
                order=pending;pending=None;execute(order)
                # A filled intent cannot fire repeatedly before replanning.
                orders=[o for o in orders if not (o["side"]==order["side"] and o.get("limit")==order.get("limit"))]
            else:
                control(ci);ci+=1

    for t,price in zip(tape["trade_ns"],tape["price"]):
        t=int(t)
        if t>=stop_time:break
        drain(t)
        if pending is not None:continue
        # Strict crossing avoids pretending that a touch proves queue priority.
        hit=[o for o in orders if (o["side"]=="buy" and price<o["limit"]) or (o["side"]=="sell" and price>o["limit"])]
        if hit:
            hit.sort(key=lambda o:(0 if o["side"]=="buy" else 1,-o["limit"] if o["side"]=="buy" else o["limit"]))
            schedule(hit[0],t)
    drain(stop_time-1)
    g.terminal_close(p)
    return p,{"eligible_bars":eligible,"lifecycle_diagnostics":dict(seen),
              "execution_variant":"single_flight_observed_cross_plus_delayed_limit_guard"}
