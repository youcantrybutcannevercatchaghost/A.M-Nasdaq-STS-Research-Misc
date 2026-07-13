# ==============================================================
# Strategy Validator — toolkit module
# By Aston Monnach  |
# ==============================================================

#!/usr/bin/env python3
"""Multi-scale RD: scan ranges at intraday / mid / swing scales, pool + dedupe."""
import rd_backtest as rd
import pandas as pd, numpy as np, json

PRESETS = {
 "intraday": dict(Kmaj=12,kmin=3,min_range_pct=0.008,max_range_pct=0.04,
     eq_after_bars=120,sfp_after_bars=150,ibos_after_bars=40,entry_after_bars=40,manage_max_bars=200,
     stop_buf_pct=0.0008,zone_min_pct=0.0008),
 "mid": dict(Kmaj=24,kmin=4,min_range_pct=0.015,max_range_pct=0.10,
     eq_after_bars=200,sfp_after_bars=250,ibos_after_bars=80,entry_after_bars=80,manage_max_bars=350,
     stop_buf_pct=0.0012,zone_min_pct=0.0012),
 "swing": dict(Kmaj=40,kmin=6,min_range_pct=0.03,max_range_pct=0.20,
     eq_after_bars=300,sfp_after_bars=400,ibos_after_bars=120,entry_after_bars=120,manage_max_bars=500,
     stop_buf_pct=0.0015,zone_min_pct=0.0015),
}

def run():
    pooled={}
    for sym,f in [("BTC","btc_15m.parquet"),("SOL","sol_15m.parquet")]:
        df=pd.read_parquet(f); alltr=[]
        print(f"\n===== {sym} =====")
        for name,params in PRESETS.items():
            for k,v in params.items(): rd.P[k]=v
            tr,fn=rd.backtest(df,sym)
            for t in tr: t["scale"]=name
            alltr.extend(tr)
            print(f"  {name:8s}: {fn['trades']} trades")
        # dedupe: same direction, entry within 6 bars = same setup caught at 2 scales
        alltr.sort(key=lambda t:(t["direction"],t["entry_i"]))
        kept=[]
        for t in alltr:
            if not any(k["direction"]==t["direction"] and abs(k["entry_i"]-t["entry_i"])<=6 for k in kept[-10:]):
                kept.append(t)
        pooled[sym]=kept
        rd.stats(kept,f"{sym} POOLED multi-scale")
        cut=str(df.ts.iloc[int(len(df)*0.6)])
        rd.stats([t for t in kept if t["entry_ts"]<cut],f"{sym} in-sample")
        rd.stats([t for t in kept if t["entry_ts"]>=cut],f"{sym} OOS")
        for name in PRESETS:
            s=[t for t in kept if t["scale"]==name]
            if s:
                R=np.array([t["R"] for t in s])
                pf=R[R>0].sum()/abs(R[R<0].sum()) if (R<0).any() else 99
                print(f"     scale {name:8s}: n={len(s):>3} win={100*(R>0).mean():>3.0f}% sumR={R.sum():>6.1f} PF={pf:.2f}")
    json.dump({s:[{k:(round(v,4) if isinstance(v,float) else v) for k,v in t.items()} for t in tr] for s,tr in pooled.items()},
              open("rd_trades.json","w"),indent=1,default=str)
    print("\n[saved pooled rd_trades.json]")
run()
