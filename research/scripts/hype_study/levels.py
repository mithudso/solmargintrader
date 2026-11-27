import json, numpy as np, pandas as pd
def load(iv):
    d=pd.DataFrame(json.load(open(f"{S}/hl_{iv}.json")))
    d["ts"]=pd.to_datetime(d.t,unit="ms",utc=True)
    for c in "ohlcv": d[c]=d[c].astype(float)
    return d.set_index("ts")[list("ohlcv")]
import sys; S=sys.argv[1]
D=load("1d"); H4=load("4h"); H1=load("1h")
px=H1.c.iloc[-1]; print("last",px, H1.index[-1])
print("\n== Daily regime")
r=np.log(D.c).diff().dropna()
print("days",len(D),"first",D.index[0].date(),"first px",D.c.iloc[0])
print("ATH",D.h.max(),D.h.idxmax().date(),"drawdown from ATH %.1f%%"%((px/D.h.max()-1)*100))
for n in (7,30,90,180,365): print(f"ret {n}d %.1f%%"%((px/D.c.iloc[-n-1]-1)*100))
print("daily vol (ann) %.0f%%"%(r.std()*np.sqrt(365)*100), "last30 %.0f%%"%(r[-30:].std()*np.sqrt(365)*100))
sma=lambda n:D.c.rolling(n).mean().iloc[-1]
print("SMA20 %.2f SMA50 %.2f SMA100 %.2f SMA200 %.2f"%(sma(20),sma(50),sma(100),sma(200)))
print("autocorr d1 %.3f  (1d), weekly %.3f"%(r.autocorr(1), np.log(D.c).diff(7).dropna().autocorr(7)))
# fractal pivots
def pivots(df,k):
    hi=[];lo=[]
    for i in range(k,len(df)-k):
        w=df.iloc[i-k:i+k+1]
        if df.h.iloc[i]==w.h.max(): hi.append((df.index[i],df.h.iloc[i]))
        if df.l.iloc[i]==w.l.min(): lo.append((df.index[i],df.l.iloc[i]))
    return hi,lo
def cluster(levels,tol=0.02):
    levels=sorted(levels); out=[]
    for p in levels:
        if out and abs(p/np.mean(out[-1])-1)<tol: out[-1].append(p)
        else: out.append([p])
    return [(np.mean(c),len(c)) for c in out]
print("\n== Pivot-cluster levels (daily k=5 + 4h k=6), 2% clustering; count = touches")
hd,ld=pivots(D,5); h4,l4=pivots(H4,6)
allp=[p for _,p in hd+ld+h4+l4]
cl=cluster(allp,0.02)
cl=[(p,n) for p,n in cl if n>=3]
for p,n in sorted(cl,reverse=True):
    tag="RESIST" if p>px else "SUPPORT"
    print(f"{p:8.2f}  touches={n:2d}  {tag}  {100*(p/px-1):+.1f}%")
print("\n== Volume-at-price (daily bars spread H-L, last 365d), top nodes")
d=D[-365:]; bins=np.linspace(d.l.min(),d.h.max(),60); vp=np.zeros(len(bins)-1)
for _,row in d.iterrows():
    m=(bins[:-1]<=row.h)&(bins[1:]>=row.l)
    if m.sum(): vp[m]+=row.v/m.sum()
idx=np.argsort(vp)[::-1][:8]
poc=[(0.5*(bins[i]+bins[i+1]),vp[i]/vp.sum()) for i in sorted(idx)]
for p,s in poc: print(f"{p:8.2f}  {100*s:4.1f}% of vol")
print("\n== Swing ranges recent (30/60/90d hi/lo) and fib levels of last major swing")
for n in (14,30,60,90,180):
    x=D[-n:]; print(f"{n:3d}d  lo {x.l.min():.2f} ({x.l.idxmin().date()})  hi {x.h.max():.2f} ({x.h.idxmax().date()})")
x=D[-180:]; hi=x.h.max(); lo=x.l.min()
print("fib retrace of 180d range:",{f:round(hi-(hi-lo)*f,2) for f in (0.236,0.382,0.5,0.618,0.786)})
# level reaction test: bounce stats at touched pivots
print("\n== Do clustered levels hold? 4h bars touching a level (within 0.5%), next 6 bars move away >=1.5% before breaking by 1.5%")
lv=[p for p,n in cl]; ok=0; tot=0; res=[]
c=H4.copy()
for p in lv:
    for i in range(len(c)-7):
        if abs(c.l.iloc[i]/p-1)<0.005 and c.c.iloc[i]>p*0.998 or abs(c.h.iloc[i]/p-1)<0.005 and c.c.iloc[i]<p*1.002:
            side = 1 if c.c.iloc[i]>=p else -1
            fut=c.iloc[i+1:i+7]
            up=((fut.h.max()/p-1)); dn=((fut.l.min()/p-1))
            held = (up>=0.015 and dn>-0.015) if side==1 else (dn<=-0.015 and up<0.015)
            broke = (dn<=-0.015) if side==1 else (up>=0.015)
            tot+=1; ok+=held; res.append((held,broke))
print("touch events",tot,"held %.0f%%"%(100*ok/max(tot,1)), "broke-through %.0f%%"%(100*np.mean([b for _,b in res]) if res else 0))
print("\n== Seasonality (1h bars, UTC): mean return by hour & weekday (bps), t-stat")
rh=np.log(H1.c).diff().dropna()
g=rh.groupby(rh.index.hour); print("hour:", {h:(round(m*1e4,1),round(m/s*np.sqrt(n),1)) for h,(m,s,n) in g.agg(['mean','std','count']).iterrows() if abs(m/s*np.sqrt(n))>2})
g=rh.groupby(rh.index.day_of_week); print("dow:", {h:(round(m*1e4,1),round(m/s*np.sqrt(n),1)) for h,(m,s,n) in g.agg(['mean','std','count']).iterrows()})
print("range (hi-lo)/c by hour top3:", (( H1.h-H1.l)/H1.c).groupby(H1.index.hour).mean().sort_values(ascending=False).head(4).round(4).to_dict())
