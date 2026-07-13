# ==============================================================
# Strategy Validator — toolkit module
# By Aston Monnach  |
# ==============================================================

#!/usr/bin/env python3
"""X-post strategy debunk: 4H close > 200 EMA -> long, SL at recent swing low, trail up on higher lows, no TP.
Long-only trend follow. Key debunk metric: vs BUY & HOLD."""
import pandas as pd, numpy as np

def ema(x,n):
    return pd.Series(x).ewm(span=n,adjust=False).mean().values

def run(df,sym):
    o,h,l,c=df.o.values,df.h.values,df.l.values,df.c.values; n=len(df)
    e=ema(c,200)
    k=3
    # confirmed pivot lows (known at i+k)
    piv=np.zeros(n,bool)
    for i in range(k,n-k):
        if l[i]==l[i-k:i+k+1].min(): piv[i]=True
    cost=0.0003
    eq=1.0; pos=False; entry=sl=0.0; peak=1.0; dd=0.0
    trades=[]; bars_in=0
    for t in range(200,n):
        if pos:
            # trail: newest confirmed swing low (pivot idx <= t-k) above current SL, formed after entry
            for j in range(t-k, max(entry_i, t-30)-1, -1):
                if 0<=j<n and piv[j] and l[j]>sl and j>entry_i:
                    sl=l[j]; break
            # stop check (bar low breaks SL)
            if l[t]<=sl:
                ex=min(o[t],sl) if o[t]<sl else sl   # gap-through fills worse
                ret=(ex/entry)-1-2*cost; eq*=(1+ret); trades.append(ret); pos=False
                mark=eq
            else:
                bars_in+=1; mark=eq*(c[t]/entry)
        else:
            if c[t]>e[t] and not np.isnan(e[t]):
                # enter at close; SL = most recent confirmed swing low
                sls=[l[j] for j in range(t-k,max(0,t-60),-1) if piv[j] and l[j]<c[t]]
                if sls:
                    entry=c[t]; sl=sls[0]; entry_i=t; pos=True; bars_in+=1; mark=eq*(c[t]/entry)
                else: mark=eq
            else: mark=eq
        peak=max(peak,mark); dd=max(dd,(peak-mark)/peak)
    if pos:  # close at end
        ret=(c[-1]/entry)-1-cost; eq*=(1+ret); trades.append(ret)
    T=np.array(trades)
    bh=c[-1]/c[200]-1
    # buy&hold max DD
    cc=c[200:]; run_peak=np.maximum.accumulate(cc); bhdd=np.max((run_peak-cc)/run_peak)
    wr=100*(T>0).mean() if len(T) else 0
    print(f"\n===== {sym} 4H  ({df.ts.iloc[0].date()} -> {df.ts.iloc[-1].date()}) =====")
    print(f"  STRATEGY : {eq:.2f}x  (+{100*(eq-1):,.0f}%)   trades={len(T)}  win={wr:.0f}%  maxDD={100*dd:.0f}%  time-in-mkt={100*bars_in/(n-200):.0f}%")
    print(f"  BUY&HOLD : {1+bh:.2f}x  (+{100*bh:,.0f}%)                          maxDD={100*bhdd:.0f}%")
    verdict = "BEATS hold" if eq>1+bh else "LOSES to hold"
    ddv = "lower DD (real benefit)" if dd<bhdd else "similar/worse DD"
    print(f"  VERDICT  : strategy {verdict}; {ddv}")
    if len(T): print(f"  avg win={100*T[T>0].mean():.1f}%  avg loss={100*T[T<0].mean():.1f}%  (trend-follow shape: low win, big winners)")

for sym,f in [("NQ","nq_4h.parquet"),("BTC","btc_4h.parquet")]:
    run(pd.read_parquet(f),sym)
