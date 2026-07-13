"""
MARKET EXPLORE — open-ended, cross-asset LOOKING (descriptive, no entries).
NQ, ES (1m 2017-25) + BTC, SOL (1m flow 2022-26) + ETH (1h). All UTC; futures also ET.
Modules (each guarded so one failure can't sink the rest):
 1 activity clock + where the day's HIGH/LOW forms
 2 volatility compression -> expansion (does quiet precede big?)
 3 momentum vs mean-reversion by horizon (what game is each instrument?)
 4 cross-asset: correlation, does CRYPTO OVERNIGHT lead the NQ open, weekend->Monday
 5 crypto OI / funding / crowd as forward-VOL and forward-return tells
Everything sub-period split. Charts in his trainer colours -> ./  ; report -> EXPLORE_REPORT.md
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np, sys, os, traceback
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")

FUT="DATA/orb-research/data/"
CF ="DATA/crypto-flow/"
OUT="DATA/market-explore/"; os.makedirs(OUT,exist_ok=True)
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"; MID="#a0a0a0"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"savefig.facecolor":BG,
  "axes.edgecolor":EDGE,"axes.labelcolor":EDGE,"text.color":EDGE,"xtick.color":EDGE,
  "ytick.color":EDGE,"axes.titlecolor":EDGE,"axes.grid":True,"grid.color":"#949494",
  "grid.linewidth":0.5,"font.size":9,"figure.dpi":110})
REP=["MARKET EXPLORE — cross-asset descriptive looking (no entries). Honest: effect sizes + sub-period splits shown.\n"]
def say(s): print(s); REP.append(s)
DAILY={}  # asset -> daily return series (UTC day) for the correlation matrix

def load_fut(sym):
    d=pd.read_parquet(FUT+f"{sym}_1m_9yr.parquet")
    d["ts"]=pd.to_datetime(d.ts,utc=True); d=d.sort_values("ts").reset_index(drop=True)
    d["et"]=d.ts.dt.tz_convert("America/New_York")
    d["ret"]=d.c.pct_change(); d.loc[d.symbol!=d.symbol.shift(),"ret"]=np.nan  # roll-mask
    return d

def load_crypto_1m(sym):
    d=pd.read_parquet(CF+f"{sym}_flow_enriched.parquet",
        columns=["ts","o","h","l","c","v","delta","oi_usd","funding","acct_ls"])
    d["ts"]=pd.to_datetime(d.ts,utc=True); d=d.sort_values("ts").reset_index(drop=True)
    d["ret"]=d.c.pct_change()
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

say("\n==================== CRYPTO ====================")
CRY={}
for sym,name in [("btcusdt","BTC"),("solusdt","SOL")]:
    try:
        d=load_crypto_1m(sym); d=d.set_index("ts")
        m1_intraday(d.reset_index().rename(columns={"ts":"utc"}),name,"utc",None)
        m2_vol(d[["o","h","l","c"]],name)
        m3_autocorr(d[["c"]],name)
        DAILY[name]=daily_ret_utc(d[["c"]])
        CRY[name]=d
    except Exception as e: say(f"[{name}] LOAD ERR {e}\n{traceback.format_exc()[:300]}")
# ETH daily from 1h
try:
    e=pd.read_parquet(FUT+"ETHUSDT_1h.parquet",columns=["ts","c"]); e["ts"]=pd.to_datetime(e.ts,utc=True)
    DAILY["ETH"]=daily_ret_utc(e.set_index("ts")[["c"]])
except Exception as ex: say(f"[ETH] ERR {ex}")

# ---------------- module 4: cross-asset ----------------
say("\n==================== CROSS-ASSET ====================")
try:
    M=pd.DataFrame(DAILY).dropna(how="all")
    cm=M.corr()
    say("[daily-return correlation matrix, UTC day, full overlap]")
    say(cm.round(2).to_string())
    fig,ax=plt.subplots(figsize=(5,4)); im=ax.imshow(cm.values,cmap="Greys",vmin=-1,vmax=1)
    ax.set_xticks(range(len(cm))); ax.set_xticklabels(cm.columns); ax.set_yticks(range(len(cm))); ax.set_yticklabels(cm.index)
    for i in range(len(cm)):
        for j in range(len(cm)):
            ax.text(j,i,f"{cm.values[i,j]:.2f}",ha="center",va="center",
                    color=EDGE if abs(cm.values[i,j])<0.6 else "#f0f0f0",fontsize=8)
    ax.set_title("daily-return correlation"); fig.colorbar(im,fraction=0.046)
    fig.tight_layout(); fig.savefig(f"{OUT}xasset_corr.png"); plt.close(fig)
except Exception as e: say(f"[xasset corr] ERR {e}")

# does CRYPTO OVERNIGHT lead the NQ open?
try:
    # NQ RTH open (first bar >=09:30 ET) and prev-day RTH close (last bar <16:00 ET)
    et=NQ.index.tz_convert("America/New_York")
    rthm=(et.time>=time(9,30))&(et.time<time(16,0))
    R=NQ[rthm].copy(); R["date"]=R.index.tz_convert("America/New_York").date
    g=R.groupby("date")
    op=g.o.first(); op_ts=g.apply(lambda x:x.index[0]); cl=g.c.last()
    fh=g.apply(lambda x: x.c.asof(x.index[0]+pd.Timedelta("60min"))/x.o.iloc[0]-1)  # first-hour ret
    day=pd.DataFrame({"open":op,"open_ts":op_ts,"rthclose":cl}).dropna()
    day["prevclose"]=day.rthclose.shift(1); day["gap"]=day.open/day.prevclose-1
    day["fh"]=fh.reindex(day.index)
    day["prevclose_ts"]=pd.Series(g.apply(lambda x:x.index[-1]).values,index=op.index).shift(1).reindex(day.index)
    # BTC close asof at those UTC timestamps
    btc=CRY["BTC"].c
    def asof(tsval):
        try: return btc.asof(pd.Timestamp(tsval))
        except Exception: return np.nan
    day=day.dropna(subset=["open_ts","prevclose_ts","gap"])
    day["btc_open"]=[asof(t) for t in day.open_ts]
    day["btc_prevclose"]=[asof(t) for t in day.prevclose_ts]
    day["btc_on"]=day.btc_open/day.btc_prevclose-1     # BTC move during NQ's overnight
    dd=day.dropna(subset=["btc_on","gap"])
    c_gap=np.corrcoef(dd.btc_on,dd.gap)[0,1]
    dd2=dd.dropna(subset=["fh"]); c_fh=np.corrcoef(dd2.btc_on,dd2.fh)[0,1]
    # sub-period
    dd["yr"]=pd.to_datetime(dd.index).year
    recent=dd[dd.yr>=2024]; c_gap_r=np.corrcoef(recent.btc_on,recent.gap)[0,1] if len(recent)>100 else np.nan
    say(f"[CRYPTO->NQ OPEN] n={len(dd)} days | corr(BTC overnight move, NQ open gap)={c_gap:+.2f} "
        f"| corr(BTC overnight, NQ first-hour ret)={c_fh:+.2f} | 2024+ gap-corr {c_gap_r:+.2f}")
    fig,ax=plt.subplots(figsize=(5.2,4))
    ax.scatter(dd.btc_on*100,dd.gap*100,s=6,color=DOWN,edgecolor="none",alpha=0.4)
    ax.set_xlabel("BTC move during NQ overnight %"); ax.set_ylabel("NQ open gap %")
    ax.set_title(f"BTC overnight vs NQ open gap  (corr {c_gap:+.2f})")
    ax.set_xlim(dd.btc_on.quantile(.01)*100,dd.btc_on.quantile(.99)*100)
    ax.set_ylim(dd.gap.quantile(.01)*100,dd.gap.quantile(.99)*100)
    fig.tight_layout(); fig.savefig(f"{OUT}crypto_leads_nq.png"); plt.close(fig)
    # weekend crypto -> Monday NQ
    day["dow"]=pd.to_datetime(day.index).dayofweek
    mon=day[day.dow==0].dropna(subset=["btc_on","gap"])
    if len(mon)>50:
        cm2=np.corrcoef(mon.btc_on,mon.gap)[0,1]
        say(f"[WEEKEND->MON] n={len(mon)} Mondays | corr(BTC weekend move, NQ Mon gap)={cm2:+.2f}")
except Exception as e: say(f"[crypto->NQ] ERR {e}\n{traceback.format_exc()[:400]}")

# ---------------- module 5: crypto OI / funding / crowd as forward tells ----------------
say("\n==================== CRYPTO OI / FUNDING / CROWD ====================")
for name in ["BTC","SOL"]:
    try:
        d=CRY[name]
        r=d.resample("1h").agg(c=("c","last"),oi=("oi_usd","last"),funding=("funding","last"),
                               acct_ls=("acct_ls","last"),h=("h","max"),l=("l","min")).dropna(subset=["c"])
        r["fwd_rng"]=((r.h.rolling(6).max().shift(-6)-r.l.rolling(6).min().shift(-6))/r.c)*100  # next-6h range
        r["fwd_ret24"]=r.c.shift(-24)/r.c-1
        r["oichg6"]=r.oi.pct_change(6)
        a=r.dropna(subset=["oichg6","fwd_rng"])
        c_oi=np.corrcoef(a.oichg6,a.fwd_rng)[0,1]
        # OI-buildup decile -> forward range
        a=a.copy(); a["dec"]=pd.qcut(a.oichg6.rank(method="first"),10,labels=False)
        oi_hi=a[a.dec==9].fwd_rng.mean(); oi_lo=a[a.dec==0].fwd_rng.mean(); oi_md=a.fwd_rng.mean()
        # funding & crowd extremes -> forward 24h return (contrarian?)
        f=r.dropna(subset=["funding","fwd_ret24"]);
        fhi=f[f.funding>=f.funding.quantile(.9)].fwd_ret24.mean()*100; flo=f[f.funding<=f.funding.quantile(.1)].fwd_ret24.mean()*100
        cr=r.dropna(subset=["acct_ls","fwd_ret24"]); c_crowd=np.corrcoef(cr.acct_ls,cr.fwd_ret24)[0,1]
        cr["yr"]=cr.index.year; cr26=cr[cr.yr>=2026]; c_c26=np.corrcoef(cr26.acct_ls,cr26.fwd_ret24)[0,1] if len(cr26)>100 else np.nan
        say(f"[{name}] OI-build->fwd6h-range corr {c_oi:+.2f} (top-decile OI build {oi_hi:.2f}% vs bottom {oi_lo:.2f}% vs avg {oi_md:.2f}%) | "
            f"funding hi->fwd24h {fhi:+.2f}% vs lo {flo:+.2f}% | crowd(acct_ls)->fwd24h corr {c_crowd:+.2f} (2026 {c_c26:+.2f})")
        fig,ax=plt.subplots(figsize=(6,3.3))
        gg=a.groupby("dec").fwd_rng.mean()
        ax.bar(gg.index,gg.values,color=[UP if v>oi_md else DOWN for v in gg.values],edgecolor=EDGE)
        ax.axhline(oi_md,color=EDGE,ls="--",lw=1.2,label=f"avg {oi_md:.2f}%")
        ax.set_title(f"{name} — next-6h RANGE by OI-buildup decile"); ax.set_xlabel("6h OI-change decile (9=biggest build)")
        ax.set_ylabel("next-6h range %"); ax.legend(); fig.tight_layout(); fig.savefig(f"{OUT}{name}_oi_vol.png"); plt.close(fig)
    except Exception as e: say(f"[{name}] m5 ERR {e}\n{traceback.format_exc()[:300]}")

open(OUT+"EXPLORE_REPORT.md","w",encoding="utf-8").write("\n".join(REP))
print("\nSaved ->",OUT)
