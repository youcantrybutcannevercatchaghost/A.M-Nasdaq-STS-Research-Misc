#!/usr/bin/env python3
"""
Faithful-AS-POSSIBLE Python port of the STS (Regular) 6-sub NQ book, for testing on
local NQ data (free-plan TV can't show the history). APPROXIMATION, not trade-for-trade
(the project's own README warns its Python parity engines diverged). Flags every simplification.

Subs (all @ bar close, ET, single position — first sub each bar takes the slot):
 S1 Trend  : 09:40 long if close>sessVWAP & mom(250)>1 ; exit close<VWAP or 16:45
 S2 L-ORB  : 09:30-09:45 range; long breakout close>rangeHi if green & close>VWAP; SL rangeLo
 S3 Short  : 09:40-15:10 short if close<VWAP & RSI(21)<25 & VIX<20; SL +1%; cover close>VWAP
 S4 S-ORB  : short breakdown close<rangeLo if red & close<VWAP; SL +0.5%
 S5 OVN    : 18:15 long if close>wVWAP & 1.0<dATR%<1.5 & VIX/VIX3M<0.95 & VIX<p75; 0.5/0.5% bracket; exit 08:30
 S6 Univ   : 09:45-12:00 long close>VWAP+1σ & close>open & ER(20)>0.65 & close>dVWAP (mirror short); SL 2.5ATR TP 6ATR
Costs: $2.05/contract commission + 2-tick (0.5pt) slippage. Tier sizing 1/2/3 by ATR%.
APPROXIMATIONS: session VWAP anchored 18:00 ET; daily aggregates on 18:00-ET SESSION bars (Pine "D"); VIX = prior-day daily.
POST-AUDIT FIXES (2026-07-09): S4 sizing=RSI/momentum tier; S5 sizing=weeklyVWAP-dist/dailyATR tier; S2 exit 16:45; S3 exit 16:45; session-anchored daily ATR%; vixp75 single-shift.
"""
import pandas as pd, numpy as np
TICK=0.25; PTVAL=20.0; COMM=2.05; SLIP=2*TICK

def load5m(path):
    df=pd.read_parquet(path)
    if "symbol" in df.columns:  # 9yr file: front-month per day
        df["d0"]=pd.to_datetime(df["ts"]).dt.date
        dom=df.groupby(["d0","symbol"])["v"].sum().reset_index().sort_values("v").drop_duplicates("d0",keep="last")[["d0","symbol"]]
        df=df.merge(dom,on=["d0","symbol"])
    df["et"]=pd.to_datetime(df["ts"]).dt.tz_convert("America/New_York")
    df=df.set_index("et").sort_index()
    r=pd.DataFrame({"o":df.o.resample("5min").first(),"h":df.h.resample("5min").max(),
                    "l":df.l.resample("5min").min(),"c":df.c.resample("5min").last(),
                    "v":df.v.resample("5min").sum()}).dropna().reset_index()
    r["date"]=r.et.dt.date; r["t"]=r.et.dt.hour*100+r.et.dt.minute
    return r

def rma(x,n):
    a=np.full(len(x),np.nan)
    if len(x)<n: return a
    a[n-1]=np.nanmean(x[:n])
    for i in range(n,len(x)): a[i]=(a[i-1]*(n-1)+x[i])/n
    return a

def build(r, vix, vix3m):
    n=len(r); h,l,c,o,v=r.h.values,r.l.values,r.c.values,r.o.values,r.v.values
    hlc3=(h+l+c)/3
    t=r.t.values
    # session id (reset 18:00 ET), week id
    newsess=(t>=1800)&(np.roll(t,1)<1800); newsess[0]=True
    sid=np.cumsum(newsess)
    iso=pd.to_datetime(r.et).dt.isocalendar()
    wid=(iso.year*100+iso.week).values
    # session VWAP + weekly VWAP (cumulative within group)
    def gvwap(gid, price):
        pv=price*v; out=np.empty(n); cs_pv=0.0; cs_v=0.0; cur=gid[0]
        for i in range(n):
            if gid[i]!=cur: cs_pv=0.0; cs_v=0.0; cur=gid[i]
            cs_pv+=pv[i]; cs_v+=v[i]; out[i]=cs_pv/cs_v if cs_v>0 else price[i]
        return out
    vwap=gvwap(sid, c)     # ta.vwap(close, isNewDay): CLOSE-weighted (was hlc3 — bug)
    wvwap=gvwap(wid, c)    # ta.vwap(close, isNewWeek): CLOSE-weighted
    atr=rma(np.maximum(h-l,np.maximum(np.abs(h-np.roll(c,1)),np.abs(l-np.roll(c,1)))),14)
    # rsi(21)
    d=np.diff(c,prepend=c[0]); up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
    rs=rma(up,21)/np.where(rma(dn,21)==0,np.nan,rma(dn,21)); rsi=100-100/(1+rs)
    mom=c-np.roll(c,250)
    # efficiency ratio (20)
    chg=np.abs(c-np.roll(c,20)); s=pd.Series(np.abs(c-np.roll(c,1))).rolling(20).sum().values
    er=np.where(s>0,chg/s,0.5)
    # daily VWAP (RTH-day reset at 00:00 ET date) for S6
    dvwap=gvwap(sid, hlc3)   # S6 manual daily VWAP: HLC3-weighted, SAME session anchor as vwapVal
    band=pd.Series(c).rolling(250).std().values
    atrPct=atr/c*100
    # daily aggregates on 18:00-ET SESSION bars (matches Pine request.security "D" for CME NQ) -> prior session
    rr=r.copy(); rr["sid"]=sid
    dfd=rr.groupby("sid").agg(H=("h","max"),L=("l","min"),C=("c","last")).reset_index()
    dfd["atr"]=rma(np.maximum(dfd.H.values-dfd.L.values,
                    np.maximum(np.abs(dfd.H.values-np.roll(dfd.C.values,1)),np.abs(dfd.L.values-np.roll(dfd.C.values,1)))),14)
    dfd["pdH"]=dfd.H.shift(1); dfd["pdL"]=dfd.L.shift(1); dfd["pdC"]=dfd.C.shift(1)
    dfd["dAtrPct"]=(dfd.atr.shift(1)/dfd.C.shift(1))*100
    dfd["dAtrPts"]=dfd.atr.shift(1)   # prior-session daily ATR in POINTS (for S5 weekly-VWAP-distance tier)
    dmap=dfd.set_index("sid")
    r2=r.copy(); r2["sid"]=sid
    for col in ["pdH","pdL","pdC","dAtrPct","dAtrPts"]: r2[col]=r2["sid"].map(dmap[col])
    # VIX prior-day + 252d p75
    vx=vix.copy(); vx["date"]=vx.Date.dt.date; vx=vx.set_index("date")["close"]
    v3=vix3m.copy(); v3["date"]=v3.Date.dt.date; v3=v3.set_index("date")["close"]
    vixp75=vix.set_index(vix.Date.dt.date)["close"].rolling(252).quantile(0.75)  # single lag applied by priormap() below
    # map prior-day vix
    alldates=sorted(set(r.date))
    vser=vix.set_index(vix.Date.dt.date)["close"]; v3ser=vix3m.set_index(vix3m.Date.dt.date)["close"]
    def priormap(ser):
        s=ser.reindex(sorted(set(list(ser.index)+alldates))).ffill().shift(1)
        return {d:s.get(d,np.nan) for d in alldates}
    pm_vix=priormap(vser); pm_v3=priormap(v3ser); pm_p75=priormap(vixp75)
    r2["vix"]=r2.date.map(pm_vix); r2["vix3m"]=r2.date.map(pm_v3); r2["vixp75"]=r2.date.map(pm_p75)
    I=dict(vwap=vwap,wvwap=wvwap,dvwap=dvwap,atr=atr,rsi=rsi,mom=mom,er=er,band=band,atrPct=atrPct,
           pdH=r2.pdH.values,pdL=r2.pdL.values,pdC=r2.pdC.values,dAtrPct=r2.dAtrPct.values,dAtrPts=r2.dAtrPts.values,
           vix=r2.vix.values,vix3m=r2.vix3m.values,vixp75=r2.vixp75.values, sid=sid)
    return I

def tier(atrPct, v3, v2):
    return 3 if atrPct<v3 else (2 if atrPct<v2 else 1)

def run(r, I, label, only=None, quiet=False):
    n=len(r); h,l,c,o=r.h.values,r.l.values,r.c.values,r.o.values; t=r.t.values; et=r.et.values
    vwap,wvwap,dvwap=I["vwap"],I["wvwap"],I["dvwap"]; atr=I["atr"]; rsi=I["rsi"]; mom=I["mom"]; er=I["er"]
    band=I["band"]; atrPct=I["atrPct"]; pdH,pdL=I["pdH"],I["pdL"]; dAtr=I["dAtrPct"]; dAtrPts=I["dAtrPts"]
    vix,vix3m,vixp75=I["vix"],I["vix3m"],I["vixp75"]
    pos=0; entry=0.0; qty=0; sub=""; sl=np.nan; tp=np.nan; entry_i=0
    eq=100000.0; trades=[]; cnt={s:0 for s in ["S1","S2","S3","S4","S5","S6"]}
    # ORB range (RTH 0930-0945)
    orbHi=orbLo=orbOpen=orbClose=np.nan; day=None
    def close_pos(i,px,reason):
        nonlocal pos,eq
        pnl=((px-entry) if pos>0 else (entry-px))*abs(qty)*PTVAL - (COMM*abs(qty)*2) - (SLIP*abs(qty)*PTVAL)
        eq+=pnl
        # --- trade anatomy: MFE/MAE (points, %, R) + entry-context features (no effect on P&L) ---
        seg_h=h[entry_i:i+1]; seg_l=l[entry_i:i+1]
        if pos>0: mfe=seg_h.max()-entry; mae=entry-seg_l.min()          # long: favorable=up, adverse=down
        else:     mfe=entry-seg_l.min(); mae=seg_h.max()-entry          # short: favorable=down, adverse=up
        risk=abs(entry-sl) if sl==sl else np.nan                        # per-trade risk = stop distance (nan if no stop)
        trades.append(dict(sub=sub,side=("L" if pos>0 else "S"),entry_ts=str(et[entry_i]),exit_ts=str(et[i]),
            entry=entry,exit=px,qty=abs(qty),pnl=pnl,eq=eq,reason=reason,hold=int(i-entry_i),
            mfe=mfe,mae=mae,mfe_pct=100*mfe/entry,mae_pct=100*mae/entry,
            mfe_R=(mfe/risk if risk==risk and risk>0 else np.nan),
            mae_R=(mae/risk if risk==risk and risk>0 else np.nan),
            t=int(t[entry_i]),vwap_dist=100*(entry-vwap[entry_i])/vwap[entry_i],
            mom=mom[entry_i],rsi=rsi[entry_i],atrpct=atrPct[entry_i],er=er[entry_i],vix=vix[entry_i]))
        pos=0
    for i in range(260,n):
        # new RTH day -> reset ORB
        if r.date.values[i]!=day:
            day=r.date.values[i]; orbHi=0.0; orbLo=1e9; orbOpen=np.nan; orbClose=np.nan
        if t[i]==930: orbOpen=o[i]
        if 930<=t[i]<945:
            orbHi=max(orbHi,h[i]); orbLo=min(orbLo,l[i])
        if t[i]==945: orbClose=c[i-1]
        orbReady = t[i]>=945 and orbHi>0
        # ---- EXITS first ----
        if pos!=0:
            px=None; rsn=None
            if sub=="S1":
                if c[i]<vwap[i]: px=c[i]; rsn="vwapx"
                elif t[i]>=1645: px=c[i]; rsn="eod"
            elif sub=="S2":
                if l[i]<=sl: px=sl; rsn="sl"
                elif t[i]>=1645: px=c[i]; rsn="eod"   # Pine: Long ORB rides to 16:45 close_all (NOT the 15:55 block)
            elif sub=="S3":
                if h[i]>=sl: px=sl; rsn="sl"
                elif c[i]>vwap[i]: px=c[i]; rsn="vwapx"
                elif t[i]>=1645: px=c[i]; rsn="eod"   # Pine: 15:10 is the ENTRY cutoff only; short rides to 16:45 close_all
            elif sub=="S4":
                if h[i]>=sl: px=sl; rsn="sl"
                elif t[i]>=1555: px=c[i]; rsn="eod"
            elif sub=="S5":
                if l[i]<=sl: px=sl; rsn="sl"
                elif h[i]>=tp: px=tp; rsn="tp"
                elif t[i]>=830 and t[i]<1600: px=c[i]; rsn="amx"
            elif sub=="S6":
                if pos>0 and (l[i]<=sl or h[i]>=tp): px=(sl if l[i]<=sl else tp); rsn="brk"
                elif pos<0 and (h[i]>=sl or l[i]<=tp): px=(sl if h[i]>=sl else tp); rsn="brk"
                elif t[i]>=1555: px=c[i]; rsn="eod"
            if px is not None: close_pos(i,px,rsn)
        # ---- ENTRIES (flat only; only=SN isolates a single sub, no cross-blocking) ----
        if pos==0 and not np.isnan(vwap[i]):
            ok=lambda s: only is None or only==s
            # S1
            if ok("S1") and t[i]==940 and c[i]>vwap[i] and mom[i]>1.0:
                q=tier(atrPct[i],0.05,0.5); pos=1;entry=c[i];qty=q;sub="S1";sl=tp=np.nan;entry_i=i;cnt["S1"]+=1
            # S2 long ORB
            elif ok("S2") and orbReady and t[i]<1530 and (orbClose>orbOpen) and c[i]>orbHi and c[i]>vwap[i]:
                q=tier(atrPct[i],0.05,0.10); pos=1;entry=c[i];qty=q;sub="S2";sl=(orbLo if orbLo<c[i] else c[i]*0.99);tp=np.nan;entry_i=i;cnt["S2"]+=1
            # S3 short
            elif ok("S3") and 940<=t[i]<1510 and c[i]<vwap[i] and rsi[i]<25 and (not np.isnan(vix[i]) and vix[i]<20):
                q=tier(atrPct[i],0.05,0.5); pos=-1;entry=c[i];qty=q;sub="S3";sl=c[i]*1.01;tp=np.nan;entry_i=i;cnt["S3"]+=1
            # S4 short ORB
            elif ok("S4") and orbReady and t[i]<1530 and (orbClose<orbOpen) and c[i]<orbLo and c[i]<vwap[i]:
                q=tier(rsi[i],10,25); pos=-1;entry=c[i];qty=q;sub="S4";sl=c[i]*1.005;tp=np.nan;entry_i=i;cnt["S4"]+=1  # Pine S4: Momentum/RSI tier (rsi<10->3, rsi<25->2)
            # S5 overnight
            elif ok("S5") and 1815<=t[i]<1830 and (not np.isnan(wvwap[i]) and c[i]>wvwap[i]) and (not np.isnan(dAtr[i]) and 1.0<dAtr[i]<1.5) \
                 and (not np.isnan(vix3m[i]) and not np.isnan(vix[i]) and vix[i]/vix3m[i]<0.95) and (not np.isnan(vixp75[i]) and vix[i]<vixp75[i]):
                dpts=dAtrPts[i]; distv7=abs(c[i]-wvwap[i])/dpts if (not np.isnan(dpts) and dpts>0) else np.nan  # Pine S5: |close-weeklyVWAP|/priorDailyATR
                q=1 if np.isnan(distv7) else (3 if distv7<=0.25 else (2 if distv7<=0.50 else 1)); pos=1;entry=c[i];qty=q;sub="S5";sl=c[i]*0.995;tp=c[i]*1.005;entry_i=i;cnt["S5"]+=1
            # S6 universal
            elif ok("S6") and 945<=t[i]<1200 and not np.isnan(band[i]):
                up=c[i]>dvwap[i]+band[i]; dn=c[i]<dvwap[i]-band[i]
                if up and c[i]>o[i] and er[i]>0.65 and c[i]>dvwap[i]:
                    q=tier(atrPct[i],0.1,0.25); pos=1;entry=c[i];qty=q;sub="S6";sl=c[i]-2.5*atr[i];tp=c[i]+6*atr[i];entry_i=i;cnt["S6"]+=1
                elif dn and c[i]<o[i] and er[i]>0.65 and c[i]<dvwap[i]:
                    q=tier(atrPct[i],0.1,0.25); pos=-1;entry=c[i];qty=q;sub="S6";sl=c[i]+2.5*atr[i];tp=c[i]-6*atr[i];entry_i=i;cnt["S6"]+=1
    T=pd.DataFrame(trades)
    print(f"\n===== {label} =====  bars={n}")
    print(f"  per-sub entries: {cnt}   total trades: {len(T)}")
    if len(T):
        net=eq-100000; win=100*(T.pnl>0).mean()
        pf=T.pnl[T.pnl>0].sum()/abs(T.pnl[T.pnl<0].sum()) if (T.pnl<0).any() else 99
        # equity curve + maxDD
        curve=100000+T.pnl.cumsum(); peak=curve.cummax(); dd=(peak-curve); mdd=dd.max()
        print(f"  NET ${net:,.0f} ({100*net/100000:+.0f}%)  win {win:.0f}%  PF {pf:.2f}  maxDD ${mdd:,.0f}  end ${eq:,.0f}")
        T["year"]=pd.to_datetime(T.entry_ts).dt.year
        yr=T.groupby("year").pnl.sum()
        print("  by year: "+"  ".join(f"{y}:{v/1000:+.0f}k" for y,v in yr.items()))
        sp=T.groupby("sub").pnl.agg(['sum','count','mean'])
        print("  by SUB:  "+"  ".join(f"{s}:{r['sum']/1000:+.0f}k(n{int(r['count'])},avg${r['mean']:.0f})" for s,r in sp.iterrows()))
    return T

if __name__=="__main__":
    vix=pd.read_parquet("vix.parquet"); vix3m=pd.read_parquet("vix3m.parquet")
    # 9-year sample
    r=load5m("DATA/orb-research/data/nq_1m_9yr.parquet")
    I=build(r,vix,vix3m); T=run(r,I,"NQ 2017-2025 (9yr)")
    T.to_parquet("sts_trades_9yr.parquet")
    # 2026 slice (compare to his forward -57%)
    r26=load5m("DATA/orb-research/data/nq_of_1m.parquet")
    I26=build(r26,vix,vix3m); run(r26,I26,"NQ 2026 (Apr-Jun, local)")
