"""
HIS 06-02 QUESTION: when price rallies into a STACKED CLUSTER, why does it REVERSE there vs PUSH THROUGH to the next target (PDH)?
For every RTH day (9yr+2026, 5m): find the first rally INTO an upside cluster (>=2 of PDH/ONH/PMH/AsiaH/LDNH within a band),
classify the next 2h as REVERSED (dropped back below the cluster) vs PUSHED (continued up / hit a target above),
then COMPARE the two groups on: approach momentum (force vs exhausted), volume at touch, rejection wick, time,
how far it already ran (extension), and whether a 5m FVG was there (his hypothesis). What actually separates them?
report -> CLUSTER_REJECT.md
"""
import pandas as pd, numpy as np, sys
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/"
R=["WHY REVERSE AT THE CLUSTER vs PUSH THROUGH — NQ 5m, upside stacked clusters. Descriptive.\n"]
def say(s): print(s); R.append(s)
BAND=0.0010
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c","v"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
rth=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"),C=("c","last"))
dts=list(rth.index); prevmap={dts[i]:dts[i-1] for i in range(1,len(dts))}
def stack(levels,band):
    levels=sorted(levels); best=None
    for i in range(len(levels)):
        grp=[x for x in levels[i:] if x-levels[i]<=band]
        if len(grp)>=2 and (best is None or len(grp)>len(best)): best=grp
    return best
def wlevels(date):
    ds=pd.Timestamp(date).tz_localize("America/New_York")
    def win(a0,b0,a1,b1,d0=0,d1=0):
        s=d[(d.index>=(ds+pd.Timedelta(days=d0)).replace(hour=a0,minute=b0))&(d.index<(ds+pd.Timedelta(days=d1)).replace(hour=a1,minute=b1))]
        return (s.h.max(),s.l.min()) if len(s) else (np.nan,np.nan)
    L={}; pr=prevmap.get(date)
    if pr is not None: L["PDH"]=rth.loc[pr].H
    L["ONH"],_=win(18,0,9,30,-1,0); L["ASIAH"],_=win(20,0,0,0,-1,0); L["LDNH"],_=win(2,0,5,0); L["PMH"],_=win(4,0,9,30)
    return {k:v for k,v in L.items() if pd.notna(v)}
rows=[]
for date,g in d[(d.t>=570)&(d.t<960)].groupby("date"):
    r=g.resample("5min").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last"),v=("v","sum")).dropna()
    if len(r)<50: continue
    o=r.o.values;h=r.h.values;l=r.l.values;c=r.c.values;v=r.v.values.astype(float);n=len(r)
    pc=pd.Series(c).shift().values; tr=np.maximum(h-l,np.maximum(np.abs(h-pc),np.abs(l-pc))); atr=pd.Series(tr).rolling(14).mean().bfill().values
    vma=pd.Series(v).rolling(20).mean().bfill().values
    L=wlevels(date); px=c[0]; band=px*BAND
    ups=[L[k] for k in L if L[k]>px]
    st=stack(ups,band)
    if st is None: continue
    ctop=max(st); cbot=min(st)
    tgt=[x for x in ups if x>ctop]; target=min(tgt) if tgt else None
    # first rally into the cluster from below
    ti=None
    for i in range(3,n):
        if h[i]>=cbot and c[i-1]<cbot: ti=i; break
    if ti is None: continue
    i=ti; a=atr[i] if atr[i]>0 else 1
    mom=(h[i]-c[max(0,i-6)])/a                      # momentum into it (ATR)
    vol=v[i]/(vma[i] or 1); wick=(h[i]-max(o[i],c[i]))/((h[i]-l[i]) or 1e9)
    ext=(cbot-l[:i+1].min())/a                       # how far it ran up to get here (ATR)
    hr=r.index[i].hour+r.index[i].minute/60
    fvg=False                                        # bearish 5m FVG near the touch (i-3..i)
    for k in range(max(2,i-3),i+1):
        if h[k]<l[k-2]: fvg=True;break
    e=min(n,i+24); fh=h[i+1:e]; fl=l[i+1:e]
    if not len(fh): continue
    hit_tgt=(target is not None) and (fh.max()>=target)
    reversed_=(fl.min()<=cbot-0.5*a) and not hit_tgt
    pushed=hit_tgt or (fh.max()>=ctop+0.75*a)
    outcome="reversed" if reversed_ else ("pushed" if pushed else "chop")
    rows.append(dict(date=date,yr=pd.Timestamp(date).year,outcome=outcome,mom=mom,vol=vol,wick=wick,ext=ext,hr=hr,fvg=fvg,stacksize=len(st),has_target=target is not None))
T=pd.DataFrame(rows)
def blk(T,tag):
    if len(T)<30: say(f"\n{tag}: only {len(T)} — skip"); return
    rv=T[T.outcome=="reversed"]; pu=T[T.outcome=="pushed"]; ch=T[T.outcome=="chop"]
    say(f"\n===== {tag} — {len(T)} cluster-rallies =====")
    say(f"  outcome: REVERSED {100*len(rv)/len(T):.0f}% | PUSHED-THROUGH {100*len(pu)/len(T):.0f}% | chop {100*len(ch)/len(T):.0f}%")
    say(f"  {'discriminator':34}{'REVERSED':>11}{'PUSHED':>11}   separates?")
    def cmp(nm,col,pct=False):
        a=rv[col].mean()*(100 if pct else 1); b=pu[col].mean()*(100 if pct else 1)
        sep='<-- YES' if abs(a-b)>(0.20*max(abs(b),1e-9)) else 'no'
        say(f"  {nm:34}{a:>11.2f}{b:>11.2f}   {sep}")
    cmp("approach momentum (ATR, into it)","mom")
    cmp("volume at touch (x avg)","vol")
    cmp("rejection wick (frac)","wick")
    cmp("how far it already ran (ATR)","ext")
    cmp("5m FVG present (his idea) %","fvg",pct=True)
    cmp("time of touch (ET hour)","hr")
blk(T,"9yr 2017-2025" ) if False else None
blk(T[T.yr<=2025],"9yr 2017-2025"); blk(T[T.yr==2026],"FRESH 2026")
say("\nREAD: 'reversed' = turned back below the cluster before reaching the target above. Compare the two columns —")
say("whatever is BIG-different between REVERSED and PUSHED is your answer to 'why did it reverse THERE'.")
open(OUT+"CLUSTER_REJECT.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved CLUSTER_REJECT.md")
