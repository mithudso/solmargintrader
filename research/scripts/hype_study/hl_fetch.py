import json, sys, time, urllib.request
def snap(interval, start, end):
    out=[]
    while start < end:
        req=urllib.request.Request("https://api.hyperliquid.xyz/info",
          data=json.dumps({"type":"candleSnapshot","req":{"coin":"HYPE","interval":interval,"startTime":start,"endTime":end}}).encode(),
          headers={"content-type":"application/json"})
        rows=json.load(urllib.request.urlopen(req,timeout=30))
        if not rows: break
        out+=rows
        nxt=rows[-1]["t"]+1
        if nxt<=start: break
        start=nxt
        if len(rows)<500: break
        time.sleep(0.3)
    return out
now=int(time.time()*1000)
for iv,days in (("1d",800),("4h",400),("1h",150),("15m",40)):
    rows=snap(iv, now-days*86400000, now)
    seen={}
    for r in rows: seen[r["t"]]=r
    rows=[seen[k] for k in sorted(seen)]
    json.dump(rows, open(f"{sys.argv[1]}/hl_{iv}.json","w"))
    print(iv,len(rows),rows[0]["t"],rows[-1]["t"])
