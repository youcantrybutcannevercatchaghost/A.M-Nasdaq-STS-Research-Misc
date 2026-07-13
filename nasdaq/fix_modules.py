"""
FIX + EXTEND: (A) does crypto OVERNIGHT lead the NQ open/day? (merge_asof, robust)
              (B) NQ high/low timing — full-sample vs fresh-2026 slice
              (C) crypto OI/funding/crowd as forward-VOL / forward-return tells (inf-safe)
NQ = 9yr (2017-25) + nq_of_1m (2026 Apr-Jun) appended so 2026 is IN the crypto->NQ test.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np, sys, traceback
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
FUT="DATA/orb-research/data/"; CF="DATA/crypto-flow/"; OUT="DATA/market-explore/"
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"savefig.facecolor":BG,"axes.edgecolor":EDGE,
  "axes.labelcolor":EDGE,"text.color":EDGE,"xtick.color":EDGE,"ytick.color":EDGE,"axes.titlecolor":EDGE,
  "axes.grid":True,"grid.color":"#949494","grid.linewidth":0.5,"font.size":9,"figure.dpi":110})
R=["\n\n========== FIX/EXTEND PASS (crypto->NQ lead, 2026-included; OI/funding/crowd) =========="]
def say(s): print(s); R.append(s)

# ---- load NQ 2017-2025 + 2026 Apr-Jun ----
nq=pd.read_parquet(FUT+"nq_1m_9yr.parquet",columns=["ts","o","h","l","c"])
nq26=pd.read_parquet(FUT+"nq_of_1m.parquet",columns=["ts","o","h","l","c"])
nq=pd.concat([nq,nq26],ignore_index=True)
nq["ts"]=pd.to_datetime(nq.ts,utc=True); nq=nq.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
nq["et"]=nq.ts.dt.tz_convert("America/New_York")
say(f"[NQ] merged {len(nq):,} 1m bars {nq.ts.min().date()} -> {nq.ts.max().date()}")

# ---- BTC 1m close ----
btc=pd.read_parquet(CF+"btcusdt_flow_enriched.parquet",columns=["ts","c"]).rename(columns={"c":"btc"})
btc["ts"]=pd.to_datetime(btc.ts,utc=True); btc=btc.sort_values("ts").reset_index(drop=True)

# ================= (A) crypto overnight -> NQ open/day =================
try:
    rth=nq[(nq.et.dt.time>=time(9,30))&(nq.et.dt.time<time(16,0))].copy()
    rth["etdate"]=rth.et.dt.date
    first=rth.groupby("etdate").first(); last=rth.groupby("etdate").last()
    day=pd.DataFrame({"open":first.o,"open_ts":first.ts,"close":last.c,"close_ts":last.ts}).dropna()
    day["prevclose"]=day.close.shift(1); day["prevclose_ts"]=day.close_ts.shift(1)
    day["gap"]=day.open/day.prevclose-1
    day["rthret"]=day.close/day.open-1
    day=day.dropna(subset=["prevclose_ts"])
    day["gapdays"]=(day.open_ts-day.prevclose_ts).dt.total_seconds()/86400
    day=day[day.gapdays<=4]                     # drop the Jan-Mar 2026 hole & long breaks
    # BTC close asof at NQ open and prev-close timestamps
    d=day.dropna(subset=["open_ts","prevclose_ts"]).copy()
    d=pd.merge_asof(d.sort_values("open_ts"),btc,left_on="open_ts",right_on="ts",direction="backward").rename(columns={"btc":"btc_open"}).drop(columns="ts")
    d=pd.merge_asof(d.sort_values("prevclose_ts"),btc,left_on="prevclose_ts",right_on="ts",direction="backward").rename(columns={"btc":"btc_prevclose"}).drop(columns="ts")
    d["btc_on"]=d.btc_open/d.btc_prevclose-1
    d=d.dropna(subset=["btc_on","gap","rthret"])
    d["yr"]=pd.to_datetime(d.open_ts).dt.year
    def cc(x,y):
        x,y=np.asarray(x,float),np.asarray(y,float); m=np.isfinite(x)&np.isfinite(y)
        return np.corrcoef(x[m],y[m])[0,1] if m.sum()>30 else np.nan
    cg=cc(d.btc_on,d.gap); cr=cc(d.btc_on,d.rthret)
    d26=d[d.yr>=2026]; dr=d[d.yr>=2022]
    say(f"[CRYPTO->NQ] n={len(d)} days (2022+ where BTC exists)")
    say(f"   corr(BTC overnight move, NQ OPEN GAP)   = {cg:+.2f}   <- do they move together into the open")
    say(f"   corr(BTC overnight move, NQ RTH day ret) = {cr:+.2f}   <- does overnight crypto PREDICT the cash-session day")
    say(f"   2026-only (n={len(d26)}): gap {cc(d26.btc_on,d26.gap):+.2f} | rthret {cc(d26.btc_on,d26.rthret):+.2f}")
    # after the gap is known, does btc_on still add? residual corr of btc_on vs (rthret) among big-overnight days
    big=d[d.btc_on.abs()>=d.btc_on.abs().quantile(.8)]
    say(f"   big BTC-overnight days (top 20% |move|, n={len(big)}): NQ RTH continues {100*(np.sign(big.btc_on)==np.sign(big.rthret)).mean():.0f}% of the time (50=coin-flip)")
    # weekend crypto -> Monday
    d["dow"]=pd.to_datetime(d.open_ts).dt.dayofweek; mon=d[d.dow==0]
    say(f"   WEEKEND->MON: corr(BTC weekend move, NQ Mon gap)={cc(mon.btc_on,mon.gap):+.2f} (n={len(mon)})")
    fig,ax=plt.subplots(1,2,figsize=(10,3.8))
    for a,(xcol,ycol,ttl) in zip(ax,[("btc_on","gap","BTC overnight vs NQ open GAP"),("btc_on","rthret","BTC overnight vs NQ RTH day")]):
        xs=d[xcol]*100; ys=d[ycol]*100
        a.scatter(xs,ys,s=6,color=DOWN,alpha=0.35,edgecolor="none")
        a.set_xlim(xs.quantile(.01),xs.quantile(.99)); a.set_ylim(ys.quantile(.01),ys.quantile(.99))
        a.axhline(0,color=EDGE,lw=.7); a.axvline(0,color=EDGE,lw=.7)
        a.set_xlabel("BTC overnight %"); a.set_ylabel(ycol+" %"); a.set_title(ttl+f"  (corr {cc(d[xcol],d[ycol]):+.2f})")
    fig.tight_layout(); fig.savefig(OUT+"crypto_leads_nq.png"); plt.close(fig)
except Exception as e: say(f"[A] ERR {e}\n{traceback.format_exc()[:400]}")

# ================= (B) NQ high/low timing: full vs 2026 =================
try:
    def hl_timing(df):
        r=df[(df.et.dt.time>=time(9,30))&(df.et.dt.time<time(16,0))].copy(); r["d"]=r.et.dt.date; r["hr"]=r.et.dt.hour
        g=r.groupby("d"); hi=r.loc[g.h.idxmax()].hr; lo=r.loc[g.l.idxmin()].hr
        return hi.value_counts(normalize=True), lo.value_counts(normalize=True)
    hi_f,lo_f=hl_timing(nq[nq.ts.dt.year<=2025]); hi26,lo26=hl_timing(nq[nq.ts.dt.year>=2026])
    say(f"[NQ HIGH/LOW timing]  full(2017-25): HIGH top hrs {hi_f.head(3).index.tolist()} ({100*hi_f.head(3).sum():.0f}%) LOW {lo_f.head(3).index.tolist()} ({100*lo_f.head(3).sum():.0f}%)")
    say(f"                      2026 Apr-Jun:  HIGH top hrs {hi26.head(3).index.tolist()} ({100*hi26.head(3).sum():.0f}%) LOW {lo26.head(3).index.tolist()} ({100*lo26.head(3).sum():.0f}%)  <- holds fresh?")
except Exception as e: say(f"[B] ERR {e}")

# ================= (C) crypto OI / funding / crowd forward tells (inf-safe) =================
for name,fn in [("BTC","btcusdt"),("SOL","solusdt")]:
    try:
        d=pd.read_parquet(CF+fn+"_flow_enriched.parquet",columns=["ts","c","h","l","oi_usd","funding","acct_ls"])
        d["ts"]=pd.to_datetime(d.ts,utc=True); d=d.set_index("ts")
        r=d.resample("1h").agg(c=("c","last"),h=("h","max"),l=("l","min"),oi=("oi_usd","last"),
                               funding=("funding","last"),acct_ls=("acct_ls","last")).dropna(subset=["c"])
        r["fwd_rng"]=((r.h.rolling(6).max().shift(-6)-r.l.rolling(6).min().shift(-6))/r.c)*100
        r["fwd24"]=r.c.shift(-24)/r.c-1
        r["oichg6"]=r.oi.pct_change(6).replace([np.inf,-np.inf],np.nan)
        a=r.replace([np.inf,-np.inf],np.nan).dropna(subset=["oichg6","fwd_rng"]).copy()
        def cc(x,y):
            x,y=np.asarray(x,float),np.asarray(y,float); m=np.isfinite(x)&np.isfinite(y)
            return np.corrcoef(x[m],y[m])[0,1] if m.sum()>30 else np.nan
        c_signed=cc(a.oichg6,a.fwd_rng); c_abs=cc(a.oichg6.abs(),a.fwd_rng)
        a["dec"]=pd.qcut(a.oichg6.rank(method="first"),10,labels=False); gg=a.groupby("dec").fwd_rng.mean(); base=a.fwd_rng.mean()
        f=r.dropna(subset=["funding","fwd24"]); fhi=f[f.funding>=f.funding.quantile(.9)].fwd24.mean()*100; flo=f[f.funding<=f.funding.quantile(.1)].fwd24.mean()*100
        cr=r.dropna(subset=["acct_ls","fwd24"]); cr26=cr[cr.index.year>=2026]
        say(f"[{name}] OI change -> next-6h range: signed corr {c_signed:+.2f} | |OI change| corr {c_abs:+.2f}  (U-shape: extremes move more)")
        say(f"        OI decile range: quietest {gg.iloc[0]:.2f}% | mid {gg.iloc[5]:.2f}% | biggest-build {gg.iloc[-1]:.2f}% (avg {base:.2f}%)")
        say(f"        funding hi->fwd24h {fhi:+.2f}% vs lo {flo:+.2f}% | crowd(acct_ls)->fwd24h corr {cc(cr.acct_ls,cr.fwd24):+.2f} (2026 {cc(cr26.acct_ls,cr26.fwd24):+.2f})")
        fig,ax=plt.subplots(figsize=(6,3.3)); ax.bar(gg.index,gg.values,color=[UP if v>base else DOWN for v in gg.values],edgecolor=EDGE)
        ax.axhline(base,color=EDGE,ls="--",lw=1.2,label=f"avg {base:.2f}%"); ax.set_title(f"{name} — next-6h RANGE by OI-change decile (0=biggest drop, 9=biggest build)")
        ax.set_xlabel("OI 6h-change decile"); ax.set_ylabel("next-6h range %"); ax.legend(); fig.tight_layout(); fig.savefig(OUT+name+"_oi_vol.png"); plt.close(fig)
    except Exception as e: say(f"[{name}] ERR {e}\n{traceback.format_exc()[:300]}")

open(OUT+"EXPLORE_REPORT.md","a",encoding="utf-8").write("\n".join(R))
print("\nappended -> EXPLORE_REPORT.md")
