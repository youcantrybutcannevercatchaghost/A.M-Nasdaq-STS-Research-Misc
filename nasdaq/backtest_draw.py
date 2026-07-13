"""
STRATEGY (verbatim from what we discussed) — "pullback to the untapped DRAW":
 LONG:  PDH is above the open and still UNTAPPED (price hasn't reached it) -> bias up.
        after price makes a session high and PULLS BACK >=0.5 ATR, enter LONG on the resumption
        bar (closes green above the prior bar's high). Stop = pullback low. Target = PDH.
 SHORT: mirror with PDL below.
 One trade/day (first valid). 5m RTH. 2pt cost. 2026 ONLY (his ask).
Saves every trade to draw_trades.csv so we can RENDER + eyeball them.
"""
import pandas as pd, numpy as np, sys
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/"
BUF=4.0; COST=2.0
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
rth=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"))
dts=list(rth.index); prevmap={dts[i]:dts[i-1] for i in range(1,len(dts))}
trades=[]
for date,g in d[(d.t>=570)&(d.t<960)].groupby("date"):
    if pd.Timestamp(date).year!=2026: continue
    if date not in prevmap: continue
    r=g.resample("5min").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).dropna().reset_index()
    o=r.o.values;h=r.h.values;l=r.l.values;c=r.c.values;n=len(r)
    if n<30: continue
    pc=pd.Series(c).shift().values; tr=np.maximum(h-l,np.maximum(np.abs(h-pc),np.abs(l-pc))); atr=pd.Series(tr).rolling(14).mean().bfill().values
    PDH=float(rth.loc[prevmap[date]].H); PDL=float(rth.loc[prevmap[date]].L); op=o[0]
    trade=None
    for i in range(6,n-1):
        a=atr[i] if atr[i]>0 else 1
        # ---- LONG toward PDH ----
        if PDH>op and h[:i].max()<PDH:                     # draw above, still untapped
            hi=int(np.argmax(h[:i])); pblow=l[hi:i+1].min(); pb=h[hi]-pblow
            if pb>=0.5*a and c[i]>h[i-1] and c[i]>o[i]:     # real pullback + resumption
                entry=c[i]; stop=pblow-BUF; tgt=PDH
                if tgt-entry>=1.0*a and entry-stop>=2:
                    trade=dict(side="long",e=i,entry=entry,stop=stop,tgt=tgt); break
        # ---- SHORT toward PDL ----
        if PDL<op and l[:i].min()>PDL:
            lo=int(np.argmin(l[:i])); pbhi=h[lo:i+1].max(); pb=pbhi-l[lo]
            if pb>=0.5*a and c[i]<l[i-1] and c[i]<o[i]:
                entry=c[i]; stop=pbhi+BUF; tgt=PDL
                if entry-tgt>=1.0*a and stop-entry>=2:
                    trade=dict(side="short",e=i,entry=entry,stop=stop,tgt=tgt); break
    if trade is None: continue
    e=trade["e"]; side=trade["side"]; entry=trade["entry"]; stop=trade["stop"]; tgt=trade["tgt"]; risk=abs(entry-stop)
    res=None; xt=None
    for k in range(e+1,n):
        if side=="long":
            if l[k]<=stop: res,xp,xt="loss",stop,k; break
            if h[k]>=tgt: res,xp,xt="win",tgt,k; break
        else:
            if h[k]>=stop: res,xp,xt="loss",stop,k; break
            if l[k]<=tgt: res,xp,xt="win",tgt,k; break
    if res is None: res,xp,xt="timeout",c[-1],n-1
    pts=((xp-entry) if side=="long" else (entry-xp))-COST; R=pts/risk if risk>0 else 0
    trades.append(dict(date=str(date),side=side,entry_time=str(r.et[e])[11:16],entry=round(entry,2),stop=round(stop,2),
        target=round(tgt,2),exit=round(xp,2),exit_time=str(r.et[xt])[11:16],result=res,pts=round(pts,1),R=round(R,2),
        risk=round(risk,1),ebar=e,xbar=xt))
T=pd.DataFrame(trades); T.to_csv(OUT+"draw_trades.csv",index=False)
print(f"===== PULLBACK-TO-DRAW — 2026 only, {len(T)} trades =====")
if len(T):
    w=(T.result=="win").sum(); ls=(T.result=="loss").sum(); to=(T.result=="timeout").sum(); net=T.pts.sum()
    print(f"  win {w} / loss {ls} / timeout {to}  ->  win% (excl timeout) {100*w/max(w+ls,1):.0f}%  |  win% (all) {100*w/len(T):.0f}%")
    print(f"  avg R/trade {T.R.mean():+.2f} | total {net:+.0f} pts | MNQ ${net*2:+,.0f} | NQ ${net*20:+,.0f}  [after {COST}pt cost]")
    print(f"  by side: "+" | ".join(f"{s}: {len(x)} trades, {x.pts.sum():+.0f}pt, {100*(x.result=='win').mean():.0f}% win" for s,x in T.groupby('side')))
    print("\n  sample trades:")
    for _,t in T.head(12).iterrows():
        print(f"   {t.date} {t.side:5} {t.entry_time} entry {t.entry:.0f} stop {t.stop:.0f} tgt {t.target:.0f} -> {t.result:7} {t.pts:+.0f}pt")
print("\nsaved draw_trades.csv")
