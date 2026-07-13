"""
LIVE 'is-the-high-in?' TRIO — CAUSAL test.  climax volume + rejection wick + buyers absorbed.
Detection uses ONLY info known at the bar. Forward-only outcomes. Benchmarked vs ordinary local highs.
Two variants so we see if 'absorbed' (delta) earns its keep:
  V1 = climax vol + rejection wick + new local high        (works without order flow)
  V2 = V1 + buyers absorbed (delta>0 AND close in low 40%) (needs delta)
Assets: BTC, SOL (full flow 2022-26), NQ-2026 (Apr-Jun flow, RTH), NQ-9yr (RTH, V1 only).
Metrics per signal, next 30 bars: net fwd return, reversal-first (1 ATR down before 1 ATR up),
and 'was-it-the-top' = price never exceeds the signal high by >0.1% over the next 2h.
report -> TRIO.md ; chart in his colours.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np, sys, traceback
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
FUT="DATA/orb-research/data/"; CF="DATA/crypto-flow/"; OUT="DATA/market-explore/"
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"; MID="#a0a0a0"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"savefig.facecolor":BG,"axes.edgecolor":EDGE,
  "axes.labelcolor":EDGE,"text.color":EDGE,"xtick.color":EDGE,"ytick.color":EDGE,"axes.titlecolor":EDGE,
  "axes.grid":True,"grid.color":"#949494","grid.linewidth":0.5,"font.size":9,"figure.dpi":110})
R=["LIVE TRIO 'is-the-high-in?' — CAUSAL. climax vol + rejection wick + buyers absorbed. vs ordinary local highs.\n"]
def say(s): print(s); R.append(s)
CHART={}

K=20; N=30; TOPWIN=120; VOLX=2.0; WICK=0.5; CLOSEPOS=0.4  # params

def prep(df, has_delta):
    o,h,l,c,v=[df[x].values.astype(float) for x in "ohlcv"]
    n=len(df)
    volma=pd.Series(v).rolling(30).mean().shift(1).values
    pc=pd.Series(c).shift().values
    tr=np.maximum(h-l,np.maximum(np.abs(h-pc),np.abs(l-pc)))
    atr=pd.Series(tr).rolling(30).mean().values
    rng=np.where(h-l==0,np.nan,h-l)
    upwick=(h-np.maximum(o,c))/rng
    closepos=(c-l)/rng
    localhigh=h>=pd.Series(h).shift(1).rolling(K).max().values
    climax=v>=VOLX*volma
    rejection=upwick>=WICK
    V1=climax&rejection&localhigh
    if has_delta:
        d=df["delta"].values.astype(float); absorbed=(d>0)&(closepos<=CLOSEPOS); V2=V1&absorbed
    else: V2=None
    control=localhigh&~V1
    return dict(o=o,h=h,l=l,c=c,v=v,atr=atr,n=n,V1=V1,V2=V2,control=control)

def outcomes(P, mask, name):
    h,l,c,atr,n=P["h"],P["l"],P["c"],P["atr"],P["n"]
    idx=np.where(mask & np.isfinite(atr) & (atr>0))[0]
    idx=idx[(idx> 40)&(idx< n-N-1)]
    if len(idx)<20: return None
    net=[]; revfirst=[]; wastop=[]
    for i in idx:
        a=atr[i]
        fh=h[i+1:i+1+N]; fl=l[i+1:i+1+N]
        net.append(c[min(i+N,n-1)]/c[i]-1)
        # reversal-first: 1 ATR down before 1 ATR up
        dn=np.where((c[i]-fl)>=a)[0]; upp=np.where((fh-c[i])>=a)[0]
        di=dn[0] if len(dn) else 1e9; ui=upp[0] if len(upp) else 1e9
        revfirst.append(di<ui)
        # was-it-the-top: price never exceeds signal high by >0.1% over next TOPWIN
        w=h[i+1:i+1+TOPWIN]; wastop.append((w.max()-h[i])/h[i] < 0.001 if len(w) else np.nan)
    net=np.array(net); return dict(n=len(idx), net=np.nanmedian(net)*100,
        revfirst=100*np.nanmean(revfirst), wastop=100*np.nanmean(wastop))

def run(path, name, cols, has_delta, rth=False):
    try:
        df=pd.read_parquet(path,columns=cols); df["ts"]=pd.to_datetime(df.ts,utc=True); df=df.sort_values("ts").reset_index(drop=True)
        if rth:
            et=df.ts.dt.tz_convert("America/New_York"); df=df[(et.dt.time>=time(9,30))&(et.dt.time<time(16,0))].reset_index(drop=True)
        ndays=df.ts.dt.date.nunique()
        P=prep(df,has_delta)
        say(f"\n===== {name} ({len(df):,} 1m bars, {ndays} days) =====")
        say(f"  {'signal':26}{'n':>7}{'/day':>7}{'fwd30 net%':>12}{'rev-first%':>12}{'was-top%':>10}")
        res={}
        for key,lab in [("control","ordinary local high"),("V1","V1 climax+wick"),("V2","V2 +absorbed")]:
            m=P[key];
            if m is None: continue
            o=outcomes(P,m,lab)
            if o: res[lab]=o; say(f"  {lab:26}{o['n']:>7}{o['n']/max(ndays,1):>7.1f}{o['net']:>12.3f}{o['revfirst']:>12.0f}{o['wastop']:>10.0f}")
        CHART[name]=res
        return res
    except Exception as e: say(f"[{name}] ERR {e}\n{traceback.format_exc()[:300]}")

run(CF+"btcusdt_flow_enriched.parquet","BTC",["ts","o","h","l","c","v","delta"],True)
run(CF+"solusdt_flow_enriched.parquet","SOL",["ts","o","h","l","c","v","delta"],True)
run(FUT+"nq_of_1m.parquet","NQ-2026",["ts","o","h","l","c","v","delta"],True,rth=True)
run(FUT+"nq_1m_9yr.parquet","NQ-9yr",["ts","o","h","l","c","v"],False,rth=True)

say("\nREAD: 'was-top%' = of signals, how often price never went >0.1% higher in next 2h (you caught the top).")
say("A signal EARNS ITS KEEP only if V1/V2 beat the 'ordinary local high' control on rev-first% and was-top%.")

# chart: was-top% by signal per asset
try:
    assets=[a for a in CHART if CHART[a]]; labels=["ordinary local high","V1 climax+wick","V2 +absorbed"]
    x=np.arange(len(assets)); w=0.26
    fig,ax=plt.subplots(figsize=(9,3.8))
    for k,(lab,col) in enumerate(zip(labels,[DOWN,MID,UP])):
        vals=[CHART[a].get(lab,{}).get("wastop",np.nan) for a in assets]
        ax.bar(x+(k-1)*w,vals,w,label=lab,color=col,edgecolor=EDGE)
    ax.set_xticks(x); ax.set_xticklabels(assets); ax.set_ylabel("'was the top' %  (next 2h)")
    ax.set_title("Trio as a live top-caller: does climax+wick(+absorb) beat an ordinary local high?"); ax.legend()
    fig.tight_layout(); fig.savefig(OUT+"trio_wastop.png"); plt.close(fig)
except Exception as e: say(f"chart ERR {e}")
open(OUT+"TRIO.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved -> TRIO.md")
