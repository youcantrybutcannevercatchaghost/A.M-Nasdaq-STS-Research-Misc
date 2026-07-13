# ==============================================================
# Strategy Validator — toolkit module
# By Aston Monnach  |
# ==============================================================

#!/usr/bin/env python3
"""
Bollinger Band DOUBLE-PURGE (WP) — proper spec, causal, with reality-check.
Purge = candle CLOSES outside the band (confirmed by user).
Long (mirror for short):
  purge1: close < lower band
  -> price tags the midline (basis) before the 2nd purge
  -> purge2: close < lower band AND makes a NEW low below purge1's low
  -> ENTRY: first candle that CLOSES back inside the band
  -> target: recent range high (rolling); SL below purge2 low; BE at midline
Runs OPTIMISTIC (signal-close entry, current-bar levels, 0.02% fee) vs
REALISTIC (next-bar-open entry, known-before-bar levels, 0.05%/side + slip).
BB 20/2, 15m.
"""
import pandas as pd, numpy as np
LEN=20; K=2.0; GAP=20; ENTRYWIN=10; RANGE_LB=60; MANAGE=150; BUF=0.0007

def bands(c):
    b=pd.Series(c).rolling(LEN).mean(); sd=pd.Series(c).rolling(LEN).std(ddof=0)
    return b.values, (b+K*sd).values, (b-K*sd).values

def detect(o,h,l,c,basis,UB,LB,n):
    setups=[]
    for side in ("long","short"):
        i=LEN+1
        while i<n-2:
            if side=="long":  p1 = c[i]<LB[i]
            else:             p1 = c[i]>UB[i]
            if not (p1 and not np.isnan(LB[i])): i+=1; continue
            p1x = l[i] if side=="long" else h[i]
            # midline tag before 2nd purge
            mj=None
            for j in range(i+1,min(i+GAP,n)):
                if (h[j]>=basis[j]) if side=="long" else (l[j]<=basis[j]): mj=j; break
            if mj is None: i+=1; continue
            # purge2: close beyond band AND new extreme past purge1
            p2=None
            for k in range(mj+1,min(mj+GAP,n)):
                if side=="long" and c[k]<LB[k] and l[k]<p1x: p2=k; p2x=l[k]; break
                if side=="short" and c[k]>UB[k] and h[k]>p1x: p2=k; p2x=h[k]; break
            if p2 is None: i+=1; continue
            # entry: first close back inside band
            en=None
            for mm in range(p2+1,min(p2+ENTRYWIN,n)):
                if (c[mm]>LB[mm]) if side=="long" else (c[mm]<UB[mm]): en=mm; break
            if en is None: i=p2+1; continue
            if side=="long":
                stop=p2x-BUF*p2x; tgt=np.max(h[max(0,en-RANGE_LB):en])
                if tgt<=c[en]: i=en+1; continue
            else:
                stop=p2x+BUF*p2x; tgt=np.min(l[max(0,en-RANGE_LB):en])
                if tgt>=c[en]: i=en+1; continue
            setups.append(dict(side=side,p2=p2,en=en,stop=stop,tgt=tgt))
            i=en+1
    setups.sort(key=lambda s:s["en"])
    return setups

def simulate(df,setups,realistic):
    o,h,l,c=df.o.values,df.h.values,df.l.values,df.c.values; n=len(df)
    basis,_,_=bands(c)
    comm=0.0005 if realistic else 0.0002; slip=0.0003 if realistic else 0.0
    T=[]; used=-1
    for s in setups:
        en=s["en"]
        if en<=used: continue
        if realistic:
            if en+1>=n: continue
            entry=o[en+1]; start=en+1
        else:
            entry=c[en]; start=en
        side=s["side"]; stop=s["stop"]; tgt=s["tgt"]
        risk=(entry-stop) if side=="long" else (stop-entry)
        if risk<=0: continue
        be=False; R=None; exi=None
        for t in range(start+1,min(start+MANAGE,n)):
            mid = basis[t-1] if realistic else basis[t]
            if side=="long":
                es=entry if be else stop
                if l[t]<=es: R=((es*(1-slip)-entry)/risk); exi=t; break
                if (not be) and h[t]>=mid: be=True
                if h[t]>=tgt: R=((tgt-entry)/risk); exi=t; break
            else:
                es=entry if be else stop
                if h[t]>=es: R=((entry-es*(1+slip))/risk); exi=t; break
                if (not be) and l[t]<=mid: be=True
                if l[t]<=tgt: R=((entry-tgt)/risk); exi=t; break
        if R is None:
            t=min(start+MANAGE,n)-1
            R=((c[t]-entry)/risk) if side=="long" else ((entry-c[t])/risk); exi=t
        # apply fees in R terms (approx: fee % of price / risk%)
        feeR = (2*comm*entry)/risk
        R-=feeR
        T.append(R); used=exi
    return np.array(T)

def stats(T,label):
    if len(T)==0: print(f"  {label}: no trades"); return
    pf=T[T>0].sum()/abs(T[T<0].sum()) if (T<0).any() else 99
    print(f"  {label}: trades={len(T)} win={100*(T>0).mean():.0f}% sumR={T.sum():+.1f} avgR={T.mean():+.3f} PF={pf:.2f}")

for sym,f in [("BTC","btc_15m.parquet"),("SOL","sol_15m.parquet")]:
    df=pd.read_parquet(f); o,h,l,c=df.o.values,df.h.values,df.l.values,df.c.values; n=len(df)
    basis,UB,LB=bands(c)
    setups=detect(o,h,l,c,basis,UB,LB,n)
    print(f"\n=== {sym} 15m ===  double-purge setups detected: {len(setups)}")
    stats(simulate(df,setups,False),f"{sym} OPTIMISTIC (signal-close entry, 0.02% fee)")
    stats(simulate(df,setups,True), f"{sym} REALISTIC  (next-open entry, known levels, 0.05%/side+slip)")
