import json, numpy as np, pandas as pd, sys
S=sys.argv[1]
def load(iv):
    d=pd.DataFrame(json.load(open(f"{S}/hl_{iv}.json"))); d["ts"]=pd.to_datetime(d.t,unit="ms",utc=True)
    for c in "ohlcv": d[c]=d[c].astype(float)
    return d.set_index("ts")[list("ohlcv")]
D=load("1d"); H4=load("4h")
# levels from DAILY pivots only, strictly using data BEFORE the test span (no lookahead): learn on first 60% of 4h span, test on rest
split=H4.index[int(len(H4)*0.6)]
Dtrain=D[D.index<split]
def pivots(df,k=5):
    lv=[]
    for i in range(k,len(df)-k):
        w=df.iloc[i-k:i+k+1]
        if df.h.iloc[i]==w.h.max(): lv.append(df.h.iloc[i])
        if df.l.iloc[i]==w.l.min(): lv.append(df.l.iloc[i])
    return np.array(sorted(lv))
lv=pivots(Dtrain)
test=H4[H4.index>=split].reset_index(drop=True)
def stat(levels,test,tol=0.005,hor=6,move=0.015):
    held=tot=0
    for p in levels:
        for i in range(len(test)-hor-1):
            near_support = abs(test.l.iloc[i]/p-1)<tol and test.c.iloc[i]>=p*0.998
            near_res = abs(test.h.iloc[i]/p-1)<tol and test.c.iloc[i]<=p*1.002
            if not (near_support or near_res): continue
            fut=test.iloc[i+1:i+1+hor]; up=fut.h.max()/p-1; dn=fut.l.min()/p-1
            h=(up>=move and dn>-move) if near_support else (dn<=-move and up<move)
            tot+=1; held+=h
    return held,tot
h,t=stat(lv,test); print(f"real pivot levels (formed pre-{split.date()}): held {h}/{t} = {100*h/max(t,1):.1f}%")
rng=np.random.default_rng(1); lo,hi=test.l.min(),test.h.max()
ctl=[]
for _ in range(200):
    r=rng.uniform(lo,hi,len(lv)); h2,t2=stat(r,test); ctl.append(h2/max(t2,1))
print(f"random levels (n=200 draws): mean held {100*np.mean(ctl):.1f}%  p95 {100*np.percentile(ctl,95):.1f}%  -> real is {'ABOVE' if h/max(t,1)>np.percentile(ctl,95) else 'within'} random band")
