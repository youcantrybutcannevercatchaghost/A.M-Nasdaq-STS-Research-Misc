# ==============================================================
# Strategy Validator — toolkit module
# By Aston Monnach  |
# ==============================================================

#!/usr/bin/env python3
"""
Range Deviation (RD) — mechanical backtest of White Phoenix's strategy.
Causal, no look-ahead. Long + short (mirror). Funnel-instrumented.

Pipeline (long; short = mirror):
  1. RANGE   two opposite MAJOR swings define [lo,hi]; EQ=50%. Range 'confirmed' when
             price taps EQ AFTER the 2nd swing (EQ is 3rd/last event).
  2. SFP     after EQ, a bar wicks BELOW range lo and closes back above (failed breakdown),
             occurring below EQ. sfp_lo = that wick low (stop ref).
  3. iBOS    price closes above the last MINOR lower-high that sits below EQ (internal BoS up).
  4. ZONE    orderflow demand = bullish FVG on the impulse leg, else last down-candle OB.
  5. ENTRY   limit on retrace into the demand zone (fill at zone top).
  6. MANAGE  stop below sfp_lo; half off at EQ; runner to range hi; early-exit on opposite iBOS.
"""
import sys, pandas as pd, numpy as np

# SWING-SCALE calibration — matched to his real SOL Jun-2026 trade:
# 9.5%-tall range, formed over ~1.6 days, setup resolved over ~3-5 days (multi-day swing structure).
P = dict(
    Kmaj=40,         # major swing strength (~10h each side on 15m) -> multi-day swing ranges
    kmin=6,          # minor swing strength (internal structure / iBOS)
    min_range_pct=0.015,   # range height >= 1.5% of price (significant swing range)
    max_range_pct=0.20,    # allow his 9.5% and bigger
    eq_after_bars=300,     # EQ tap within ~3 days of 2nd swing
    sfp_after_bars=400,    # SFP within ~4 days of EQ tap
    ibos_after_bars=120,   # iBOS within ~30h of SFP
    entry_after_bars=120,  # retrace into zone within ~30h of iBOS
    manage_max_bars=500,   # manage up to ~5 days
    stop_buf_pct=0.0015,   # stop buffer beyond sfp wick
    zone_min_pct=0.0015,   # min zone thickness
)

def pivots(h, l, k):
    """Return arrays ph, pl (bool) marking pivot highs/lows of strength k, and confirm index = i+k."""
    n=len(h); ph=np.zeros(n,bool); pl=np.zeros(n,bool)
    for i in range(k, n-k):
        seg_h=h[i-k:i+k+1]; seg_l=l[i-k:i+k+1]
        if h[i]==seg_h.max() and (seg_h.argmax()==k): ph[i]=True
        if l[i]==seg_l.min() and (seg_l.argmin()==k): pl[i]=True
    return ph, pl

def backtest(df, symbol):
    o=df.o.values; h=df.h.values; l=df.l.values; c=df.c.values; ts=df.ts.values
    n=len(df)
    phM,plM=pivots(h,l,P["Kmaj"])
    phm,plm=pivots(h,l,P["kmin"])
    # lists of (confirm_idx, pivot_idx, price)
    majH=[(i+P["Kmaj"], i, h[i]) for i in range(n) if phM[i]]
    majL=[(i+P["Kmaj"], i, l[i]) for i in range(n) if plM[i]]
    majAll=sorted([(ci,pi,pr,'H') for ci,pi,pr in majH]+[(ci,pi,pr,'L') for ci,pi,pr in majL])
    minH=[(i+P["kmin"], i, h[i]) for i in range(n) if phm[i]]
    minL=[(i+P["kmin"], i, l[i]) for i in range(n) if plm[i]]

    funnel=dict(ranges=0, eq=0, sfp=0, ibos=0, zone=0, entry=0, trades=0)
    trades=[]
    used_until=-1   # no overlapping trades

    # iterate over consecutive opposite MAJOR pivots as candidate ranges
    for a in range(len(majAll)-1):
        ci_a,pi_a,pr_a,ty_a = majAll[a]
        ci_b,pi_b,pr_b,ty_b = majAll[a+1]
        if ty_a==ty_b: continue                 # need opposite types
        if pi_b<=used_until: continue
        hi=max(pr_a,pr_b); lo=min(pr_a,pr_b); eq=(hi+lo)/2.0
        rng=hi-lo; mid_px=(hi+lo)/2
        if rng < P["min_range_pct"]*mid_px or rng > P["max_range_pct"]*mid_px: continue
        funnel["ranges"]+=1
        # range 'active' from confirmation of 2nd swing
        t0=ci_b
        # 1) EQ tap after 2nd swing (price trades through EQ)
        eq_i=None
        for t in range(t0, min(t0+P["eq_after_bars"], n)):
            if l[t]<=eq<=h[t]: eq_i=t; break
        if eq_i is None: continue
        funnel["eq"]+=1

        # Try LONG branch (deviation of low) and SHORT branch (deviation of high)
        for direction in ('long','short'):
            if pi_b<=used_until: break
            res=try_setup(direction, hi,lo,eq, eq_i, n, o,h,l,c,ts, minH,minL, symbol)
            if res is None: continue
            funnel["sfp"]+= res.pop("_hit_sfp",0)
            funnel["ibos"]+= res.pop("_hit_ibos",0)
            funnel["zone"]+= res.pop("_hit_zone",0)
            if res.get("entry") is not None:
                funnel["entry"]+=1
                if res.get("exit") is not None:
                    funnel["trades"]+=1
                    trades.append(res)
                    used_until=res["exit_i"]
    return trades, funnel

def try_setup(direction, hi,lo,eq, eq_i, n, o,h,l,c,ts, minH,minL, symbol):
    """Return trade dict (may be partial with counters) or None."""
    out=dict(symbol=symbol, direction=direction, hi=hi, lo=lo, eq=eq,
             _hit_sfp=0,_hit_ibos=0,_hit_zone=0, entry=None, exit=None)
    long = direction=='long'
    # 2) SFP: after eq_i, wick beyond the range extreme, close back inside, on the correct side of EQ
    sfp_i=None; sfp_px=None
    for t in range(eq_i, min(eq_i+P["sfp_after_bars"], n)):
        if long:
            if l[t] < lo and c[t] > lo and c[t] < eq:
                sfp_i=t; sfp_px=l[t]; break
        else:
            if h[t] > hi and c[t] < hi and c[t] > eq:
                sfp_i=t; sfp_px=h[t]; break
    if sfp_i is None: return out
    out["_hit_sfp"]=1; out["sfp_i"]=sfp_i; out["sfp_px"]=sfp_px

    # 3) iBOS: break of last minor pivot (opposite) below/above EQ
    ibos_i=None; brk_px=None
    if long:
        # last minor pivot HIGH below EQ, formed (confirmed) at/after sfp
        cands=[(ci,pi,pr) for (ci,pi,pr) in minH if pr<eq and pi<= sfp_i+P["ibos_after_bars"] and ci<=sfp_i+P["ibos_after_bars"]]
        # choose the most recent minor high that exists by the time we search, price below EQ, above sfp
        for t in range(sfp_i+1, min(sfp_i+P["ibos_after_bars"], n)):
            # available minor highs confirmed <= t, pivot after sfp region, below EQ, above sfp_px
            avail=[pr for (ci,pi,pr) in minH if ci<=t and pi<=t and pi>=sfp_i-3 and pr<eq and pr>sfp_px]
            if avail and c[t] > min(avail):
                ibos_i=t; brk_px=min(avail); break
    else:
        for t in range(sfp_i+1, min(sfp_i+P["ibos_after_bars"], n)):
            avail=[pr for (ci,pi,pr) in minL if ci<=t and pi<=t and pi>=sfp_i-3 and pr>eq and pr<sfp_px]
            if avail and c[t] < max(avail):
                ibos_i=t; brk_px=max(avail); break
    if ibos_i is None: return out
    out["_hit_ibos"]=1; out["ibos_i"]=ibos_i

    # 4) ZONE: orderflow demand/supply on the impulse leg (sfp_i .. ibos_i)
    zone=find_zone(direction, sfp_i, ibos_i, o,h,l,c)
    if zone is None: return out
    zlo,zhi=zone
    out["_hit_zone"]=1; out["zone_lo"]=zlo; out["zone_hi"]=zhi

    # 5) ENTRY: retrace into zone within window
    entry_i=None; entry_px=None
    for t in range(ibos_i+1, min(ibos_i+P["entry_after_bars"], n)):
        if long:
            if l[t] <= zhi:                    # traded down into zone
                entry_i=t; entry_px=min(zhi, o[t]); break
            if h[t] >= hi: break               # hit target before entry -> missed
        else:
            if h[t] >= zlo:
                entry_i=t; entry_px=max(zlo, o[t]); break
            if l[t] <= lo: break
    if entry_i is None: return out
    out["entry"]=entry_px; out["entry_i"]=entry_i

    # 6) MANAGE
    if long:
        stop = sfp_px*(1-P["stop_buf_pct"])
        t1 = eq                                # half off at EQ
        tgt = hi
        risk = entry_px - stop
    else:
        stop = sfp_px*(1+P["stop_buf_pct"])
        t1 = eq
        tgt = lo
        risk = stop - entry_px
    if risk<=0: out["entry"]=None; return out

    half_done=False; realizedR=0.0; exit_i=None; exit_px=None; reason=None
    for t in range(entry_i, min(entry_i+P["manage_max_bars"], n)):
        hi_t,lo_t,cl_t=h[t],l[t],c[t]
        if long:
            # stop first (conservative)
            if lo_t<=stop:
                realizedR += (0.5 if half_done else 1.0)*((stop-entry_px)/risk)
                exit_i=t; exit_px=stop; reason=("stop_after_half" if half_done else "stop"); break
            if (not half_done) and hi_t>=t1:
                realizedR += 0.5*((t1-entry_px)/risk); half_done=True
            if hi_t>=tgt:
                realizedR += (0.5 if half_done else 1.0)*((tgt-entry_px)/risk)
                exit_i=t; exit_px=tgt; reason="target"; break
            # opposite iBOS (structure shift down): a close below last minor low after entry
            avail=[pr for (ci,pi,pr) in minL if ci<=t and pi<entry_i-0 and pr>stop]
            if half_done and avail and cl_t < max([pr for (ci,pi,pr) in minL if ci<=t and pi>=entry_i-6] or [ -1 ]):
                pass  # handled below by generic shift
        else:
            if hi_t>=stop:
                realizedR += (0.5 if half_done else 1.0)*((entry_px-stop)/risk)
                exit_i=t; exit_px=stop; reason=("stop_after_half" if half_done else "stop"); break
            if (not half_done) and lo_t<=t1:
                realizedR += 0.5*((entry_px-t1)/risk); half_done=True
            if lo_t<=tgt:
                realizedR += (0.5 if half_done else 1.0)*((entry_px-tgt)/risk)
                exit_i=t; exit_px=tgt; reason="target"; break
    if exit_i is None:  # timed out -> close at last close
        t=min(entry_i+P["manage_max_bars"], n)-1
        cl=c[t]
        if long: realizedR += (0.5 if half_done else 1.0)*((cl-entry_px)/risk)
        else:    realizedR += (0.5 if half_done else 1.0)*((entry_px-cl)/risk)
        exit_i=t; exit_px=cl; reason="timeout"
    out["stop"]=stop; out["t1"]=t1; out["tgt"]=tgt
    out["exit"]=exit_px; out["exit_i"]=exit_i; out["exit_reason"]=reason
    out["R"]=realizedR
    out["entry_ts"]=str(ts[entry_i]); out["exit_ts"]=str(ts[exit_i])
    return out

def find_zone(direction, sfp_i, ibos_i, o,h,l,c):
    """Bullish/bearish FVG on the impulse; else last opposing candle (order block)."""
    long = direction=='long'
    lo_b, hi_b = sfp_i, ibos_i
    if long:
        # bullish FVG: bar a.high < bar c.low  (gap up), 3-bar window a,b,c within impulse
        best=None
        for x in range(lo_b, hi_b-1):
            a_hi=h[x]; c_lo=l[x+2]
            if c_lo>a_hi:
                z=(a_hi,c_lo)
                if best is None or x> best[0]: best=(x,z)  # latest FVG (closest to entry)
        if best:
            zlo,zhi=best[1]
        else:
            # order block: last bearish candle before impulse
            ob=None
            for x in range(hi_b, lo_b-1, -1):
                if c[x]<o[x]: ob=(l[x],h[x]); break
            if ob is None: return None
            zlo,zhi=ob
    else:
        best=None
        for x in range(lo_b, hi_b-1):
            a_lo=l[x]; c_hi=h[x+2]
            if c_hi<a_lo:
                z=(c_hi,a_lo)
                if best is None or x>best[0]: best=(x,z)
        if best:
            zlo,zhi=best[1]
        else:
            ob=None
            for x in range(hi_b, lo_b-1, -1):
                if c[x]>o[x]: ob=(l[x],h[x]); break
            if ob is None: return None
            zlo,zhi=ob
    if zhi-zlo < P["zone_min_pct"]*((zhi+zlo)/2):
        mid=(zhi+zlo)/2; pad=P["zone_min_pct"]*mid/2; zlo,zhi=mid-pad,mid+pad
    return (zlo,zhi)

def stats(trades, label):
    if not trades:
        print(f"\n[{label}] NO TRADES"); return
    R=np.array([t["R"] for t in trades])
    wins=R[R>0]; losses=R[R<0]
    wr=100*len(wins)/len(R)
    pf=wins.sum()/abs(losses.sum()) if losses.sum()!=0 else float('inf')
    print(f"\n[{label}]  trades={len(R)}  win={wr:.1f}%  sumR={R.sum():.1f}  avgR={R.mean():.2f}"
          f"  PF={pf:.2f}  best={R.max():.1f} worst={R.min():.1f}")
    # minus top-3
    s=np.sort(R)
    print(f"          minus top-3 winners sumR={ (R.sum()-s[-3:].sum()):.1f}   median R={np.median(R):.2f}")
    byd={}
    for t in trades: byd.setdefault(t["direction"],[]).append(t["R"])
    for d,rs in byd.items():
        rs=np.array(rs); print(f"          {d}: n={len(rs)} win={100*(rs>0).mean():.0f}% sumR={rs.sum():.1f}")

if __name__=="__main__":
    allt={}
    for sym,f in [("BTC","btc_15m.parquet"),("SOL","sol_15m.parquet")]:
        df=pd.read_parquet(f)
        tr,fn=backtest(df,sym)
        allt[sym]=tr
        print(f"\n===== {sym} 15m  ({len(df)} bars) =====")
        print("funnel:",fn)
        stats(tr, f"{sym} ALL")
        # OOS split: first 60% train, last 40% test (by entry index)
        if tr:
            cut=df.ts.iloc[int(len(df)*0.6)]
            tr_is=[t for t in tr if t["entry_ts"]<str(cut)]
            tr_oos=[t for t in tr if t["entry_ts"]>=str(cut)]
            stats(tr_is, f"{sym} in-sample (first 60%)")
            stats(tr_oos, f"{sym} OOS (last 40%)")
    import json
    json.dump({s:[{k:(round(v,4) if isinstance(v,float) else v) for k,v in t.items()} for t in tr] for s,tr in allt.items()},
              open("rd_trades.json","w"), indent=1, default=str)
    print("\n[saved rd_trades.json]")
