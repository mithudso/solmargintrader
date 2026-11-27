import pandas as pd, numpy as np, json, zlib
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",110); pd.set_option("display.max_columns",30); pd.set_option("display.max_rows",200)
d=pd.concat([pd.read_csv(f"strategies-{i}.csv.gz") for i in ("1m","5m","10m","1h")]); d=d[(d.status=="completed")&(d.family!="benchmark")]
plan=json.loads(zlib.decompress(open("run-plan.json.zlib","rb").read()))
name={}
for c in plan["catalogue"]["candidates"]:
    m=c["config"]["members"]
    nm=("+".join(x["strategy"] for x in m)) if len(m)>1 else m[0]["strategy"]
    if len(m)>1: nm=c["config"]["mode"]+"["+nm+"]"
    par=",".join(f"{k}={round(v,4) if isinstance(v,float) else v}" for x in m[:2] for k,v in sorted(x["params"].items()))
    name[c["candidate_id"]]=(nm,par)
d["strat"]=d.candidate_id.map(lambda k:name[k][0]); d["params"]=d.candidate_id.map(lambda k:name[k][1])
HOLD="826ac5e44df8d3f9099c60b3"
FEE=10
x=d[(d.fee_bps_per_fill==FEE)]
h=x[(x.candidate_id==HOLD)&(x["mode"]=="baseline")].pivot_table(index="interval",columns="split",values="total_return")
print("PASSIVE HOLD @10bps"); print(h.round(4))
p=x.pivot_table(index=["interval","mode","candidate_id"],columns="split",values="total_return")
tr=x[x.split=="full"].set_index(["interval","mode","candidate_id"]).trade_count.rename("trades")
dd=x[x.split=="full"].set_index(["interval","mode","candidate_id"]).max_drawdown.rename("maxdd")
p=p.join(tr).join(dd).reset_index()
p["strat"]=p.candidate_id.map(lambda k:name[k][0]); p["params"]=p.candidate_id.map(lambda k:name[k][1])
for iv in ("1m","5m","10m","1h"):
    q=p[(p.interval==iv)]
    ok=q[(q.full>0)&(q.validation>0)&(q.test>0)&(q.trades>=10)].sort_values("full",ascending=False)
    print(f"\n=== {iv}: {len(ok)} of {len(q)} candidate x mode rows positive in FULL, VALIDATION and TEST (>=10 trades), 10bps")
    print(ok.head(12)[["mode","strat","params","full","validation","test","trades","maxdd"]].round(4).to_string(index=False))
# robust across fees: positive full at 60 bps
y=d[(d.fee_bps_per_fill==60)&(d.split=="full")]
print("\nPositive FULL return even at 60bps:",(y.total_return>0).sum(),"of",len(y)); 
print(y[y.total_return>0].groupby(["interval","strat","mode"]).total_return.max().sort_values(ascending=False).head(10).round(4))
# strategy-type league table at 10 bps, full
f=x[(x.split=="full")&(x["mode"]=="baseline")]
lt=f.groupby(["interval","strat"]).total_return.agg(["median","max","count"]).round(4)
for iv in ("5m","10m","1h"):
    print(f"\nLEAGUE {iv} baseline full (10bps): best medians"); print(lt.loc[iv].sort_values("median",ascending=False).head(8))
