"""
Modules (each guarded so one failure can't sink the rest):
 1 activity clock + where the day's HIGH/LOW forms
 2 volatility compression -> expansion (does quiet precede big?)
 3 momentum vs mean-reversion by horizon (what game is each instrument?)
Everything sub-period split. Charts in his trainer colours -> ./  ; report -> EXPLORE_REPORT.md
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np, sys, os, traceback
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")

FUT="DATA/orb-research/data/"
OUT="DATA/market-explore/"; os.makedirs(OUT,exist_ok=True)
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"; MID="#a0a0a0"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"savefig.facecolor":BG,
  "axes.edgecolor":EDGE,"axes.labelcolor":EDGE,"text.color":EDGE,"xtick.color":EDGE,
  "ytick.color":EDGE,"axes.titlecolor":EDGE,"axes.grid":True,"grid.color":"#949494",
  "grid.linewidth":0.5,"font.size":9,"figure.dpi":110})
def say(s): print(s); REP.append(s)
DAILY={}  # asset -> daily return series (UTC day) for the correlation matrix

def load_fut(sym):
    d=pd.read_parquet(FUT+f"{sym}_1m_9yr.parquet")
    d["ts"]=pd.to_datetime(d.ts,utc=True); d=d.sort_values("ts").reset_index(drop=True)
    d["et"]=d.ts.dt.tz_convert("America/New_York")
    d["ret"]=d.c.pct_change(); d.loc[d.symbol!=d.symbol.shift(),"ret"]=np.nan  # roll-mask
    return d


# ---------------- module 1: activity clock + HIGH/LOW-of-day timing ----------------
def m1_intraday(d, name, tzcol, rth=None):
    try:
        t=d[tzcol]; hr=t.dt.hour + t.dt.minute/60.0
        bucket=(hr//0.5)*0.5
        act=d.assign(b=bucket).groupby("b").ret.apply(lambda s:s.abs().mean()*1e4)  # bps
        # high/low of day timing
        dd=d.assign(date=t.dt.date, hb=t.dt.hour)
        if rth is not None:
            mask=(t.dt.time>=rth[0])&(t.dt.time<rth[1]); dd=dd[mask]
        gi=dd.groupby("date")
        hi_hr=dd.loc[gi.h.idxmax()].hb.values; lo_hr=dd.loc[gi.l.idxmin()].hb.values
        fig,ax=plt.subplots(1,2,figsize=(12,3.3))
        ax[0].bar(act.index,act.values,width=0.45,color=UP,edgecolor=EDGE,linewidth=.3)
        ax[0].set_title(f"{name} — activity by time ({'ET' if tzcol=='et' else 'UTC'}, mean |1m ret| bps)")
        ax[0].set_xlabel("hour")
        bins=np.arange(0,25)-0.5
        ax[1].hist(hi_hr,bins=bins,color=UP,edgecolor=EDGE,alpha=0.9,label="day HIGH")
        ax[1].hist(lo_hr,bins=bins,color=DOWN,edgecolor=EDGE,alpha=0.7,label="day LOW")
        ax[1].set_title(f"{name} — hour the day's HIGH / LOW forms"); ax[1].set_xlabel("hour"); ax[1].legend()
        fig.tight_layout(); fig.savefig(f"{OUT}{name}_intraday.png"); plt.close(fig)
        # report peak windows
        pk=act.sort_values(ascending=False).head(3).index.tolist()
        hh=pd.Series(hi_hr).value_counts(normalize=True); ll=pd.Series(lo_hr).value_counts(normalize=True)
        say(f"[{name}] busiest {'ET' if tzcol=='et' else 'UTC'} half-hours ~ {pk} | "
            f"day-HIGH peaks hr {hh.head(3).index.tolist()} ({100*hh.head(3).sum():.0f}% in top-3h) | "
            f"day-LOW peaks hr {ll.head(3).index.tolist()} ({100*ll.head(3).sum():.0f}%)")
    except Exception as e: say(f"[{name}] m1 ERR {e}")

# ---------------- module 2: vol compression -> expansion (daily) ----------------
def m2_vol(dclose, name):
    try:
        r=dclose.resample("1D").agg(h=("h","max"),l=("l","min"),c=("c","last"),o=("o","first")).dropna()
        r["rng"]=(r.h-r.l)/r.c*100
        r["prior"]=r.rng.rolling(10).mean().shift(1)     # trailing avg range, causal
        r["fwd"]=r.rng.shift(-1)                          # next-day range
        g=r.dropna(subset=["prior","fwd"]).copy()
        g["dec"]=pd.qcut(g.prior,10,labels=False,duplicates="drop")
        m=g.groupby("dec").fwd.mean()
        base=g.fwd.mean()
        # extreme-quiet bucket forward move
        q=g[g.dec==0]; expand=(q.fwd> g.rng.median()).mean()*100
        fig,ax=plt.subplots(figsize=(6,3.3))
        ax.bar(m.index,m.values,color=[DOWN if v<base else UP for v in m.values],edgecolor=EDGE)
        ax.axhline(base,color=EDGE,ls="--",lw=1.2,label=f"avg next-day range {base:.2f}%")
        ax.set_title(f"{name} — next-day range by PRIOR-vol decile"); ax.set_xlabel("prior-vol decile (0=quietest)")
        ax.set_ylabel("next-day range %"); ax.legend()
        fig.tight_layout(); fig.savefig(f"{OUT}{name}_volexp.png"); plt.close(fig)
        corr=g[["prior","fwd"]].corr().iloc[0,1]
        say(f"[{name}] vol clustering: corr(prior10d range, next-day range)={corr:+.2f} | "
            f"quietest-decile next-day range {m.get(0,np.nan):.2f}% vs avg {base:.2f}% "
            f"(quiet {'PERSISTS' if m.get(0,base)<base else 'expands'})")
    except Exception as e: say(f"[{name}] m2 ERR {e}\n{traceback.format_exc()[:300]}")

# ---------------- module 3: momentum vs mean-reversion by horizon ----------------
def m3_autocorr(dclose, name):
    try:
        out={}
        for tf,rule in [("5m","5min"),("15m","15min"),("1h","1h"),("4h","4h"),("1D","1D")]:
            c=dclose.c.resample(rule).last().dropna(); rr=c.pct_change().dropna()
            if len(rr)>200: out[tf]=rr.autocorr(lag=1)
        s=pd.Series(out)
        fig,ax=plt.subplots(figsize=(6,3.2))
        ax.bar(range(len(s)),s.values,color=[UP if v>0 else DOWN for v in s.values],edgecolor=EDGE)
        ax.set_xticks(range(len(s))); ax.set_xticklabels(s.index)
        ax.axhline(0,color=EDGE,lw=1); ax.set_title(f"{name} — lag-1 return autocorr by horizon (+momentum / -reversion)")
        fig.tight_layout(); fig.savefig(f"{OUT}{name}_autocorr.png"); plt.close(fig)
        say(f"[{name}] autocorr "+" ".join(f"{k}:{v:+.3f}" for k,v in out.items()))
    except Exception as e: say(f"[{name}] m3 ERR {e}")

# ---------------- module 4 helpers ----------------
def daily_ret_utc(dclose):
    c=dclose.c.resample("1D").last().dropna(); return c.pct_change().dropna()

# ============================ RUN ============================
say("==================== FUTURES ====================")
for sym,name,rth in [("nq","NQ",(time(9,30),time(16,0))),("es","ES",(time(9,30),time(16,0)))]:
    try:
        d=load_fut(sym); d=d.set_index("ts")
        m1_intraday(d.reset_index(),name,"et",rth)
        m2_vol(d[["o","h","l","c"]],name)
        m3_autocorr(d[["c"]],name)
        DAILY[name]=daily_ret_utc(d[["c"]])
        # keep RTH open/close for module 4 (NQ)
        if sym=="nq":
            NQ=d.copy()
        del d
    except Exception as e: say(f"[{name}] LOAD ERR {e}")



open(OUT+"EXPLORE_REPORT.md","w",encoding="utf-8").write("\n".join(REP))
print("\nSaved ->",OUT)
