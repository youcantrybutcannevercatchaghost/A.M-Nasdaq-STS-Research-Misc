# ==============================================================
# Aston Monnach — crypto strategy adaptations (from the STS S3 + S6 subs)
# By Aston Monnach  |
# ==============================================================
"""
Two of the STS book's strongest NQ subs, ADAPTED to 24/7 crypto (BTC/SOL 15m) and independently re-tested.
Adaptations (flagged): no VIX (crypto has none), no RTH time-gate (24/7), VWAP anchored 00:00 UTC.

  strat_rsishort  (from S3): short when close<dailyVWAP & RSI(21)<25 ; SL +1% ; cover on VWAP reclaim
  strat_univ      (from S6): breakout of dailyVWAP ± 1σ, in a trending regime (ER>0.65), aligned w/ VWAP;
                             ATR stop 2.5x / target 6x

Costs: 0.05%/side taker + slippage on stops. Single position. Realistic (next-bar-open) fills.
Outputs: printed stats + gauntlet verdict + a trades CSV per symbol/strat.
"""
import os, sys, pandas as pd, numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
try: from strategy_validator import validate
except Exception: validate=None
FEE=0.0005; SLIP=0.0003

def rma(x,n):
    a=np.full(len(x),np.nan); a[n-1]=np.nanmean(x[:n])
    for i in range(n,len(x)): a[i]=(a[i-1]*(n-1)+x[i])/n
    return a
def indicators(df):
    o,h,l,c,v=[df[x].values.astype(float) for x in ("o","h","l","c","v")]; n=len(df)
    ts=pd.to_datetime(df.ts); day=ts.dt.date.values
    hlc3=(h+l+c)/3
    # daily VWAP (00:00 UTC anchor)
    vw=np.empty(n); cs_pv=cs_v=0.0; cur=day[0]
    for i in range(n):
        if day[i]!=cur: cs_pv=cs_v=0.0; cur=day[i]
        cs_pv+=c[i]*v[i]; cs_v+=v[i]; vw[i]=cs_pv/cs_v if cs_v>0 else c[i]
    d=np.diff(c,prepend=c[0]); up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
    rs=rma(up,21)/np.where(rma(dn,21)==0,np.nan,rma(dn,21)); rsi=100-100/(1+rs)
    atr=rma(np.maximum(h-l,np.maximum(np.abs(h-np.roll(c,1)),np.abs(l-np.roll(c,1)))),14)
    chg=np.abs(c-np.roll(c,20)); ssum=pd.Series(np.abs(c-np.roll(c,1))).rolling(20).sum().values
    er=np.where(ssum>0,chg/ssum,0.5)
    band=pd.Series(c).rolling(250).std().values
    return dict(o=o,h=h,l=l,c=c,ts=ts.values,vwap=vw,rsi=rsi,atr=atr,er=er,band=band)

def backtest(I, strat):
    o,h,l,c,ts=I["o"],I["h"],I["l"],I["c"],I["ts"]; n=len(c)
    pos=0; entry=sl=tp=0.0; ei=0; eqR=[]; trades=[]
    for i in range(260,n-1):
        if pos!=0:
            px=None
            if pos>0:
                if l[i]<=sl: px=sl*(1-SLIP)
                elif not np.isnan(tp) and h[i]>=tp: px=tp
                elif strat.get("exit_long") and strat["exit_long"](I,i): px=c[i]
            else:
                if h[i]>=sl: px=sl*(1+SLIP)
                elif not np.isnan(tp) and l[i]<=tp: px=tp
                elif strat.get("exit_short") and strat["exit_short"](I,i): px=c[i]
            if i-ei>=strat.get("maxbars",400): px=c[i]
            if px is not None:
                r=((px-entry)/entry if pos>0 else (entry-px)/entry)-2*FEE
                risk=abs(entry-sl_at)/entry
                trades.append(dict(entry_ts=str(ts[ei]),exit_ts=str(ts[i]),side="long" if pos>0 else "short",
                                   entry=entry,exit=px,ret=r,R=r/risk if risk>0 else 0.0)); pos=0
        if pos==0:
            sig=strat["entry"](I,i)   # returns (dir, sl, tp) or None
            if sig:
                pos,sl,tp=sig; entry=o[i+1]; ei=i+1; sl_at=sl
    return pd.DataFrame(trades)

# ---------- STRATEGY 1: RSI mean-reversion short (from S3) ----------
def strat_rsishort():
    def entry(I,i):
        if I["c"][i]<I["vwap"][i] and I["rsi"][i]<25:
            e=I["o"][i+1]; return (-1, e*1.01, np.nan)   # short, SL +1%, no TP (VWAP-reclaim exit)
        return None
    def exit_short(I,i): return I["c"][i]>I["vwap"][i]
    return dict(entry=entry, exit_short=exit_short, maxbars=200, name="RSI-short")

# ---------- STRATEGY 2: Universal breakout-trend (from S6) ----------
def strat_univ():
    def entry(I,i):
        c,o,vw,bd,er,atr=I["c"][i],I["o"][i],I["vwap"][i],I["band"][i],I["er"][i],I["atr"][i]
        if np.isnan(bd) or np.isnan(atr): return None
        e=I["o"][i+1]
        if c>vw+bd and c>o and er>0.65 and c>vw: return (1, e-2.5*atr, e+6*atr)
        if c<vw-bd and c<o and er>0.65 and c<vw: return (-1, e+2.5*atr, e-6*atr)
        return None
    return dict(entry=entry, maxbars=400, name="Universal-trend")

def report(df, strat, label):
    I=indicators(df); T=backtest(I, strat)
    if len(T)==0: print(f"  {label}: no trades"); return T
    win=100*(T.ret>0).mean(); net=100*((1+T.ret).prod()-1)
    pf=T.ret[T.ret>0].sum()/abs(T.ret[T.ret<0].sum()) if (T.ret<0).any() else 99
    print(f"\n  {label}: trades={len(T)}  win={win:.0f}%  netROI={net:+.0f}%  PF={pf:.2f}  avg={100*T.ret.mean():+.3f}%/trade")
    return T

if __name__=="__main__":
    import os
    base=os.path.dirname(__file__)
    for sym,f in [("BTC","btc_15m.parquet"),("SOL","sol_15m.parquet")]:
        df=pd.read_parquet(os.path.join(base,f))
        for mk,strat in [("rsishort",strat_rsishort()),("univ",strat_univ())]:
            T=report(df, strat, f"{sym} · {strat['name']}")
            if len(T):
                T.to_csv(os.path.join(base,f"trades_{sym}_{mk}.csv"), index=False)
                if validate:
                    validate([{"R":float(r),"entry_ts":t} for r,t in zip(T.R,T.entry_ts)], f"{sym} {strat['name']}")
