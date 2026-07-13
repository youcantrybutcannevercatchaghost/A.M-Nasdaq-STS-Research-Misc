"""
FIGURES for the discretionary read (quantify what the eye saw). NQ RTH, 9yr(2017-25) vs 2026.
A) day-type mix: trend-from-open vs mid-close(reversal/range); how often an extreme is set in the FIRST HOUR
B) big moves = trend days? (top-decile range: % directional close, % extreme-early, size)
C) does the FIRST HOUR predict the day? strong directional 1st hr -> P(day continues) + further move, vs baseline
D) his pool read: how often the early extreme SWEEPS an overnight pool (ONH/PMH/PDH etc)
report -> READ_FIGURES.md
"""
import pandas as pd, numpy as np, sys
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/"
R=["FIGURES FOR THE READ — NQ RTH. Objective day classification; first-hour causal (known 10:30, rest measured forward).\n"]
def say(s): print(s); R.append(s)
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c","v"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d["date"]=d.et.dt.date; d["t"]=d.et.dt.hour*60+d.et.dt.minute; d["mfo"]=d.t-570
# prior-day + overnight levels for the sweep figure
rthg=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"),C=("c","last"))
dts=list(rthg.index); prevmap={dts[i]:dts[i-1] for i in range(1,len(dts))}
onh=d[(d.t>=1080)|(d.t<570)].copy()  # rough overnight (>=18:00 or <09:30) — same calendar tag ok for level magnitude
rows=[]
for date,g in d[(d.t>=570)&(d.t<960)].groupby("date"):
    g=g.sort_values("t"); o=g.o.values; h=g.h.values; l=g.l.values; c=g.c.values; mfo=g.mfo.values; n=len(g)
    if n<120: continue
    op=o[0]; dh=h.max(); dl=l.min(); dc=c[-1]; rng=dh-dl
    if rng<=0: continue
    fh=g[g.mfo<60];
    if len(fh)<20: continue
    fhh=fh.h.max(); fhl=fh.l.min(); fhc=fh.c.values[-1]; fhr=fhh-fhl
    hi_min=mfo[h.argmax()]; lo_min=mfo[l.argmin()]
    rec=dict(date=date,yr=pd.Timestamp(date).year,rng=rng,close_pos=(dc-dl)/rng,
             hi_min=hi_min,lo_min=lo_min,extreme_early=min(hi_min,lo_min)<60,
             fhr=fhr,fh_pos=(fhc-fhl)/fhr if fhr>0 else .5,fh_dir=np.sign(fhc-op),
             fhc=fhc,dc=dc,op=op)
    # sweep: if an extreme is in first hr, did it poke just past an overnight pool?
    pr=prevmap.get(date)
    lv_hi=[]; lv_lo=[]
    if pr is not None: lv_hi.append(rthg.loc[pr].H); lv_lo.append(rthg.loc[pr].L)
    ov=d[(d.date==date)&(d.t>=240)&(d.t<570)]  # premarket 04:00-09:30 as pool proxy
    if len(ov): lv_hi.append(ov.h.max()); lv_lo.append(ov.l.min())
    tol=op*0.0008; swept=False
    if hi_min<60 and lv_hi: swept=any(0<=dh-L<=tol for L in lv_hi)
    if lo_min<60 and lv_lo: swept=swept or any(0<=L-dl<=tol for L in lv_lo)
    rec["early_sweep"]=swept
    rows.append(rec)
T=pd.DataFrame(rows)
def blk(T,tag):
    n=len(T); trend=(T.close_pos.sub(.5).abs()>=.30); midc=(T.close_pos.sub(.5).abs()<=.15)
    say(f"\n===== {tag} — {n} days =====")
    say(f"A) DAY-TYPE: directional close (trend) {100*trend.mean():.0f}% | closed-middle (reversal/range) {100*midc.mean():.0f}% "
        f"| at least one extreme in FIRST HOUR {100*T.extreme_early.mean():.0f}%")
    say(f"   of TREND days, extreme set in first hour: {100*T[trend].extreme_early.mean():.0f}%  (i.e. trend-FROM-OPEN)")
    big=T[T.rng>=T.rng.quantile(.9)]
    say(f"B) BIG MOVES (top-decile range, >= {T.rng.quantile(.9):.0f}p): directional-close {100*(big.close_pos.sub(.5).abs()>=.30).mean():.0f}% "
        f"| extreme-early {100*big.extreme_early.mean():.0f}% | median range {big.rng.median():.0f}p vs all-day median {T.rng.median():.0f}p")
    # C first hour predicts
    strong=T[(T.fhr>=T.fhr.quantile(.66)) & ((T.fh_pos>=.8)|(T.fh_pos<=.2))]
    up=strong[strong.fh_pos>=.8]; dn=strong[strong.fh_pos<=.2]
    contU=100*(up.dc>up.fhc).mean() if len(up) else np.nan; furU=(up.dc-up.fhc).median() if len(up) else np.nan
    contD=100*(dn.dc<dn.fhc).mean() if len(dn) else np.nan; furD=(dn.fhc-dn.dc).median() if len(dn) else np.nan
    base=100*((T.dc-T.fhc)*T.fh_dir>0).mean()
    say(f"C) FIRST-HOUR -> DAY: strong UP-drive (n={len(up)}): day continues up {contU:.0f}%, +{furU:.0f}p more after 10:30 | "
        f"strong DOWN-drive (n={len(dn)}): continues down {contD:.0f}%, +{furD:.0f}p | baseline continue {base:.0f}%")
    say(f"   of strong-first-hour days, day closes directional (trend day): {100*(strong.close_pos.sub(.5).abs()>=.30).mean():.0f}% vs all-days {100*trend.mean():.0f}%")
    say(f"D) HIS POOL READ: of days with an extreme in the first hour, it SWEPT an overnight/PD pool (<=0.08%): {100*T[T.extreme_early].early_sweep.mean():.0f}%")
blk(T[T.yr<=2025],"9yr 2017-2025")
blk(T[T.yr==2026],"FRESH 2026")
open(OUT+"READ_FIGURES.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved READ_FIGURES.md")
