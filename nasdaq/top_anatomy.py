"""
ANATOMY OF THE DAILY TOP/BOTTOM  (NQ 9yr RTH + ES echo + NQ-2026 flow).
DESCRIPTIVE, look-ahead allowed (we describe the KNOWN high/low to train the eye).
Answers: (1) WHEN it forms (minute), (2) "is it already in?" base-rate by time of day,
(3) what the top BAR looks like (wick, volume), (4) how fast/far it reverses after,
(5) open-made vs close-made tops, (6) NQ-2026 order-flow at the top (delta).
Charts in his trainer colours -> market-explore/ ; report -> TOP_ANATOMY.md
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np, sys, traceback
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
FUT="DATA/orb-research/data/"; OUT="DATA/market-explore/"
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"; MID="#a0a0a0"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"savefig.facecolor":BG,"axes.edgecolor":EDGE,
  "axes.labelcolor":EDGE,"text.color":EDGE,"xtick.color":EDGE,"ytick.color":EDGE,"axes.titlecolor":EDGE,
  "axes.grid":True,"grid.color":"#949494","grid.linewidth":0.5,"font.size":9,"figure.dpi":110})
R=["ANATOMY OF THE DAILY TOP/BOTTOM — descriptive (look-ahead ok). NQ RTH 09:30-16:00 ET.\n"]
def say(s): print(s); R.append(s)
OPEN_END=90; CLOSE_START=330  # minutes-from-open: open window 0-90 (9:30-11:00), close 330-390 (15:00-16:00)

def load_rth(path, cols):
    d=pd.read_parquet(path,columns=cols); d["ts"]=pd.to_datetime(d.ts,utc=True)
    d=d.sort_values("ts").reset_index(drop=True); et=d.ts.dt.tz_convert("America/New_York")
    d["date"]=et.dt.date; d["mfo"]=(et.dt.hour*60+et.dt.minute)-(9*60+30)
    return d[(et.dt.time>=time(9,30))&(et.dt.time<time(16,0))].copy()

def anatomize(df, name, flowcol=None):
    rows=[]
    for date,g in df.groupby("date"):
        h=g.h.values; l=g.l.values; o=g.o.values; c=g.c.values; v=g.v.values.astype(float); mfo=g.mfo.values
        fl=g[flowcol].values.astype(float) if flowcol else None
        n=len(g)
        if n<60: continue
        hi=int(h.argmax()); lo=int(l.argmin())
        rng=h[hi]-l[lo]; vm=v.mean() or 1
        span=lambda x: (x if x>0 else 1e-9)
        wick_up=(h[hi]-max(o[hi],c[hi]))/span(h[hi]-l[hi])
        wick_dn=(min(o[lo],c[lo])-l[lo])/span(h[lo]-l[lo])
        base_up=np.nanmean((h-np.maximum(o,c))/np.where(h-l==0,np.nan,h-l))
        base_dn=np.nanmean((np.minimum(o,c)-l)/np.where(h-l==0,np.nan,h-l))
        def revdown(k):  # points off the high in next k min
            e=min(n,hi+1+k); return (h[hi]-l[hi+1:e].min()) if e>hi+1 else 0.0
        def revup(k):
            e=min(n,lo+1+k); return (h[lo+1:e].max()-l[lo]) if e>lo+1 else 0.0
        rec=dict(date=date,hi_min=mfo[hi],lo_min=mfo[lo],rng=rng,day_high=h[hi],
                 wick_up=wick_up,wick_dn=wick_dn,base_up=base_up,base_dn=base_dn,
                 vol_hi=v[hi]/vm,vol_lo=v[lo]/vm,
                 rev30=revdown(30),rev60=revdown(60),revup30=revup(30),
                 top_win=("open" if mfo[hi]<OPEN_END else "close" if mfo[hi]>=CLOSE_START else "mid"),
                 yr=pd.Timestamp(date).year)
        if fl is not None:
            w=slice(max(0,hi-2),min(n,hi+3)); rec["flow_at_hi"]=np.nansum(fl[w]); rec["cumflow_hi"]=np.nansum(fl[:hi+1])
        rows.append(rec)
    T=pd.DataFrame(rows); N=len(T)
    say(f"\n===== {name} — {N} RTH days =====")
    # (1) timing
    say(f"[WHEN] day HIGH forms: open-window(9:30-11:00) {100*(T.hi_min<OPEN_END).mean():.0f}% | "
        f"close-window(15:00-16:00) {100*(T.hi_min>=CLOSE_START).mean():.0f}% | midday {100*((T.hi_min>=OPEN_END)&(T.hi_min<CLOSE_START)).mean():.0f}%")
    say(f"       median high-minute {int(T.hi_min.median())} min after open | LOW similar (open {100*(T.lo_min<OPEN_END).mean():.0f}% close {100*(T.lo_min>=CLOSE_START).mean():.0f}%)")
    # (2) "is it in" base-rate curve
    marks=[30,60,90,120,180,240,300,330,360];
    say("[IS IT IN?] by X min after open, % of days whose HIGH is already set (never exceeded later):")
    say("       "+" | ".join(f"{m}m({['9:30','10:00','10:30','11:00','12:00','13:00','14:00','14:30','15:00','15:30'][[0,30,60,90,120,180,240,300,330,360].index(m)] if m in [0,30,60,90,120,180,240,300,330,360] else ''}): {100*(T.hi_min<=m).mean():.0f}%" for m in marks))
    # (3) anatomy
    say(f"[TOP BAR] upper-wick fraction {T.wick_up.mean():.2f} vs avg bar {T.base_up.mean():.2f} ({T.wick_up.mean()/T.base_up.mean():.1f}x) | "
        f"volume at the high {T.vol_hi.median():.1f}x the day's avg minute")
    say(f"[BOT BAR] lower-wick fraction {T.wick_dn.mean():.2f} vs avg bar {T.base_dn.mean():.2f} ({T.wick_dn.mean()/T.base_dn.mean():.1f}x) | volume {T.vol_lo.median():.1f}x avg")
    # (4) reversal after
    r30=T.rev30; r60=T.rev60
    say(f"[AFTER THE TOP] pts given back — next 30min: median {r30.median():.0f} (p75 {r30.quantile(.75):.0f}) | "
        f"next 60min: median {r60.median():.0f} (p75 {r60.quantile(.75):.0f})  [NQ pts; ~${20}/pt]")
    say(f"                as % of price: 30min {100*(r30/T.day_high).median():.2f}% | 60min {100*(r60/T.day_high).median():.2f}%")
    # (5) open vs close tops
    for w in ["open","close"]:
        s=T[T.top_win==w]
        if len(s)>30:
            say(f"       {w}-window tops (n={len(s)}): reverse {s.rev60.median():.0f} pts median in next 60min | wick {s.wick_up.mean():.2f} | vol {s.vol_hi.median():.1f}x")
    # (6) flow
    if flowcol and "flow_at_hi" in T:
        say(f"[FLOW @ TOP] {name} order-flow delta in the 5 bars around the high: median {T.flow_at_hi.median():+.0f} "
            f"(neg = aggressive SELLERS hitting into the high) | days with negative delta-at-high {100*(T.flow_at_hi<0).mean():.0f}%")
    # ---- charts ----
    try:
        fig,ax=plt.subplots(1,2,figsize=(12,3.4))
        ax[0].hist(T.hi_min,bins=np.arange(0,395,10),color=UP,edgecolor=EDGE,linewidth=.3,label="HIGH")
        ax[0].hist(T.lo_min,bins=np.arange(0,395,10),color=DOWN,edgecolor=EDGE,linewidth=.3,alpha=.65,label="LOW")
        ax[0].axvspan(0,OPEN_END,color=MID,alpha=.25); ax[0].axvspan(CLOSE_START,390,color=MID,alpha=.25)
        ax[0].set_title(f"{name} — minute the day HIGH/LOW forms (shaded=open/close)"); ax[0].set_xlabel("min after 9:30"); ax[0].legend()
        xs=np.arange(0,391,10); ph=[100*(T.hi_min<=m).mean() for m in xs]; pl=[100*(T.lo_min<=m).mean() for m in xs]
        ax[1].plot(xs,ph,color=EDGE,lw=2,label="HIGH already in"); ax[1].plot(xs,pl,color=DOWN,lw=2,ls="--",label="LOW already in")
        ax[1].axvspan(0,OPEN_END,color=MID,alpha=.25); ax[1].axvspan(CLOSE_START,390,color=MID,alpha=.25)
        ax[1].set_title(f"{name} — P(day's extreme is ALREADY IN) by time"); ax[1].set_xlabel("min after 9:30"); ax[1].set_ylabel("%"); ax[1].legend()
        fig.tight_layout(); fig.savefig(OUT+f"{name}_top_when.png"); plt.close(fig)
        fig,ax=plt.subplots(1,2,figsize=(11,3.4))
        ax[0].hist(T.rev60.clip(upper=T.rev60.quantile(.98)),bins=40,color=DOWN,edgecolor=EDGE,linewidth=.3)
        ax[0].axvline(T.rev60.median(),color=EDGE,ls="--",lw=1.4,label=f"median {T.rev60.median():.0f} pts")
        ax[0].set_title(f"{name} — pts given back in 60min AFTER the high"); ax[0].set_xlabel("points"); ax[0].legend()
        cats=["upper-wick\n(top bar)","upper-wick\n(avg bar)","volume\n(top vs avg)"]
        vals=[T.wick_up.mean(),T.base_up.mean(),T.vol_hi.median()]
        ax[1].bar(cats,vals,color=[UP,MID,DOWN],edgecolor=EDGE); ax[1].set_title(f"{name} — what the top BAR looks like")
        fig.tight_layout(); fig.savefig(OUT+f"{name}_top_bar.png"); plt.close(fig)
    except Exception as e: say(f"[{name}] chart ERR {e}")
    return T

try:
    nq=load_rth(FUT+"nq_1m_9yr.parquet",["ts","o","h","l","c","v"])
    anatomize(nq,"NQ")
except Exception as e: say(f"NQ ERR {e}\n{traceback.format_exc()[:400]}")
try:
    es=load_rth(FUT+"es_1m_9yr.parquet",["ts","o","h","l","c","v"])
    anatomize(es,"ES")
except Exception as e: say(f"ES ERR {e}\n{traceback.format_exc()[:300]}")
try:
    nqf=load_rth(FUT+"nq_of_1m.parquet",["ts","o","h","l","c","v","delta"])
    anatomize(nqf,"NQ_2026flow",flowcol="delta")
except Exception as e: say(f"NQflow ERR {e}\n{traceback.format_exc()[:300]}")

open(OUT+"TOP_ANATOMY.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved -> TOP_ANATOMY.md")
