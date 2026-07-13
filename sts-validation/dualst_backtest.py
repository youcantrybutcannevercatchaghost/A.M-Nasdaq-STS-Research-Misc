# ==============================================================
# Strategy Validator — toolkit module
# By Aston Monnach  |
# ==============================================================

#!/usr/bin/env python3
"""Faithful-ish Python port of 'BTC/NQ Dual ST Momentum PRO' — backtest on BTC & SOL 15m.
Note: approximation of the Pine (bar-based, stop-checked-before-TP). TV run is authoritative."""
import pandas as pd, numpy as np

def rma(x,n):
    out=np.full(len(x),np.nan); out[n-1]=np.nanmean(x[:n])
    for i in range(n,len(x)): out[i]=(out[i-1]*(n-1)+x[i])/n
    return out
def atr(h,l,c,n):
    pc=np.concatenate([[c[0]],c[:-1]])
    tr=np.maximum(h-l,np.maximum(np.abs(h-pc),np.abs(l-pc)))
    return rma(tr,n)
def supertrend(h,l,c,length,mult):
    n=len(c); hl2=(h+l)/2; a=atr(h,l,c,length)
    upb=hl2+mult*a; lob=hl2-mult*a
    fub=np.full(n,np.nan); flb=np.full(n,np.nan); st=np.full(n,np.nan); d=np.full(n,np.nan)
    start=int(np.argmax(~np.isnan(a)))          # first valid ATR index
    fub[start]=upb[start]; flb[start]=lob[start]; st[start]=upb[start]; d[start]=1
    for i in range(start+1,n):
        fub[i]=upb[i] if (upb[i]<fub[i-1] or c[i-1]>fub[i-1]) else fub[i-1]
        flb[i]=lob[i] if (lob[i]>flb[i-1] or c[i-1]<flb[i-1]) else flb[i-1]
        if st[i-1]==fub[i-1]:
            d[i]=-1 if c[i]>fub[i] else 1
        else:
            d[i]=1 if c[i]<flb[i] else -1
        st[i]=flb[i] if d[i]==-1 else fub[i]
    d[np.isnan(d)]=1
    return st,d
def percentrank(x,n):
    out=np.full(len(x),np.nan)
    for i in range(n,len(x)):
        w=x[i-n:i]; out[i]=100*np.mean(w<=x[i])
    return out

def run(df,sym):
    h,l,c=df.h.values,df.l.values,df.c.values; n=len(df)
    fST,fD=supertrend(h,l,c,7,2.0); sST,sD=supertrend(h,l,c,21,3.0)
    a14=atr(h,l,c,14); pr=percentrank(a14,200); volOk=pr>=10
    fChg=np.concatenate([[False]],)  # placeholder
    fChg=np.concatenate([[False],(fD[1:]!=fD[:-1])])
    longSig=(sD==-1)&(fD==-1)&fChg&volOk
    shortSig=(sD==1)&(fD==1)&fChg&volOk
    eq=1.0; pos=0; entry=tp=0; ei=0; comm=0.0002
    trades=[]; peak=1.0; maxdd=0
    for i in range(1,n):
        if pos==0:
            if longSig[i]: pos=1; entry=c[i]; tp=entry+1.5*a14[i]; ei=i
            elif shortSig[i]: pos=-1; entry=c[i]; tp=entry-1.5*a14[i]; ei=i
        else:
            ex=None; px=None
            if pos==1:
                if l[i]<=fST[i]: px=fST[i]; ex="SL"
                elif h[i]>=tp: px=tp; ex="TP"
                elif sD[i]==1: px=c[i]; ex="flip"
                elif i-ei>=20: px=c[i]; ex="time"
                if ex:
                    ret=(px-entry)/entry-2*comm; eq*=(1+ret); trades.append(ret); pos=0
            else:
                if h[i]>=fST[i]: px=fST[i]; ex="SL"
                elif l[i]<=tp: px=tp; ex="TP"
                elif sD[i]==-1: px=c[i]; ex="flip"
                elif i-ei>=20: px=c[i]; ex="time"
                if ex:
                    ret=(entry-px)/entry-2*comm; eq*=(1+ret); trades.append(ret); pos=0
        peak=max(peak,eq); maxdd=max(maxdd,(peak-eq)/peak)
    T=np.array(trades)
    if len(T)==0: print(f"[{sym}] no trades"); return
    w=T[T>0]; ls=T[T<0]
    pf=w.sum()/abs(ls.sum()) if ls.sum() else 99
    print(f"[{sym} 15m]  trades={len(T)}  win={100*(T>0).mean():.0f}%  net={100*(eq-1):+.0f}%  PF={pf:.2f} "
          f"avg={100*T.mean():+.3f}%/trade  maxDD={100*maxdd:.0f}%")

for sym,f in [("BTC","btc_15m.parquet"),("SOL","sol_15m.parquet")]:
    run(pd.read_parquet(f),sym)
print("\n(2yr, 15m. Approximation of the Pine — TV Strategy Tester is the authoritative run.)")
