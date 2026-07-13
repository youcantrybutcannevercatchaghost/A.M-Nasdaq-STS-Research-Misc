"""
STACKED 'is-the-high-in?' as an ACTUAL ENTRY (no 2h wait). CAUSAL, forward-only, structure-based stop.
Signal: trio (climax vol + rejection wick + buyers-absorbed[delta]) at a new-K-high.
Confirmation: no new high for C=10 min  (this is the 'no-new-high-in-X' tilt + it removes the ones still ripping).
Entry: at the confirmation bar. Stop: the signal HIGH. Target: 2R. Manage/timeout: M=30 min.
Outcome per signal in R (win +2 / stop -1 / else mark-to-close). Expectancy = mean R. vs ORDINARY local-high control.
Stacks (NQ): S0 trio+confirm  ->  S1 + entry after 12:00 ET.  Bottoms = mirror.
Gate: NQ-9yr (robust) AND NQ-2026 (fresh) must BOTH be positive to mean anything. GROSS (no costs) — noted.
report -> STACKED.md ; chart his colours.
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
R=["STACKED ENTRY TEST — trio + confirm(no-new-high 10m) [+late-day], stop=structure high/low, target 2R, 30m manage. GROSS.\n"]
def say(s): print(s); R.append(s)
CHART={}
K=20; C=10; M=30; VOLX=2.0; WICK=0.5; CLOSEPOS=0.4

def prep(df, has_delta):
    o,h,l,c,v=[df[x].values.astype(float) for x in "ohlcv"]; n=len(df)
    volma=pd.Series(v).rolling(30).mean().shift(1).values
    localhigh=h>=pd.Series(h).shift(1).rolling(K).max().values
    locallow =l<=pd.Series(l).shift(1).rolling(K).min().values
    rng=np.where(h-l==0,np.nan,h-l)
    upw=(h-np.maximum(o,c))/rng; dnw=(np.minimum(o,c)-l)/rng
    clpos=(c-l)/rng; climax=v>=VOLX*volma
    hrET=df["_hr"].values if "_hr" in df else np.full(n,np.nan)
    d=df["delta"].values.astype(float) if has_delta else None
    topsig=climax&(upw>=WICK)&localhigh & ((d>0)&(clpos<=CLOSEPOS) if has_delta else True)
    botsig=climax&(dnw>=WICK)&locallow  & ((d<0)&(clpos>=1-CLOSEPOS) if has_delta else True)
    topctl=localhigh&~topsig; botctl=locallow&~botsig
    return dict(o=o,h=h,l=l,c=c,n=n,hr=hrET,topsig=topsig,botsig=botsig,topctl=topctl,botctl=botctl)

def entries(P, side, mask, late=False):
    h,l,c,n,hr=P["h"],P["l"],P["c"],P["n"],P["hr"]
    outs=[]; sig=np.where(mask)[0]; sig=sig[(sig>40)&(sig<n-C-M-1)]
    for i in sig:
        e=i+C
        if side>0:  # top/short: need no new high i+1..e, entry below the high
            if h[i+1:e+1].max()>h[i]: continue
            entry=c[e]; stop=h[i]; Rr=stop-entry
            if Rr<=0: continue
            if late and not (hr[e]>=12): continue
            res=None
            for k in range(e+1,min(e+1+M,n)):
                if h[k]>=stop: res=-1.0; break
                if l[k]<=entry-2*Rr: res=2.0; break
            if res is None: res=(entry-c[min(e+M,n-1)])/Rr
        else:       # bottom/long
            if l[i+1:e+1].min()<l[i]: continue
            entry=c[e]; stop=l[i]; Rr=entry-stop
            if Rr<=0: continue
            if late and not (hr[e]>=12): continue
            res=None
            for k in range(e+1,min(e+1+M,n)):
                if l[k]<=stop: res=-1.0; break
                if h[k]>=entry+2*Rr: res=2.0; break
            if res is None: res=(c[min(e+M,n-1)]-entry)/Rr
        outs.append(res)
    a=np.array(outs)
    if len(a)<15: return None
    return dict(n=len(a), win=100*np.mean(a>0), exp=np.mean(a))

def run(path,name,cols,has_delta,rth=False,nq=False):
    try:
        df=pd.read_parquet(path,columns=cols); df["ts"]=pd.to_datetime(df.ts,utc=True); df=df.sort_values("ts").reset_index(drop=True)
        et=df.ts.dt.tz_convert("America/New_York")
        if rth:
            m=(et.dt.time>=time(9,30))&(et.dt.time<time(16,0)); df=df[m].reset_index(drop=True); et=et[m].reset_index(drop=True)
        df["_hr"]=et.dt.hour.values
        nd=df.ts.dt.date.nunique(); P=prep(df,has_delta)
        say(f"\n===== {name} ({len(df):,} bars, {nd} days) =====")
        say(f"  {'group':30}{'n':>7}{'/day':>7}{'win%':>7}{'exp(R)':>9}")
        groups=[("TOP control","topctl",1,False),("TOP trio+confirm","topsig",1,False)]
        if nq: groups.append(("TOP trio+confirm+late","topsig",1,True))
        groups+=[("BOT control","botctl",-1,False),("BOT trio+confirm","botsig",-1,False)]
        if nq: groups.append(("BOT trio+confirm+late","botsig",-1,True))
        res={}
        for lab,key,side,late in groups:
            o=entries(P,side,P[key],late)
            if o: res[lab]=o; say(f"  {lab:30}{o['n']:>7}{o['n']/max(nd,1):>7.2f}{o['win']:>7.0f}{o['exp']:>+9.2f}")
        CHART[name]=res; return res
    except Exception as e: say(f"[{name}] ERR {e}\n{traceback.format_exc()[:300]}")

run(FUT+"nq_1m_9yr.parquet","NQ-9yr",["ts","o","h","l","c","v"],False,rth=True,nq=True)
run(FUT+"nq_of_1m.parquet","NQ-2026",["ts","o","h","l","c","v","delta"],True,rth=True,nq=True)

say("\nREAD: exp(R) = average R per signal (target 2R / stop 1R at the structure high/low). >0 = edge; but must clear costs")
say("and hold on BOTH NQ-9yr and fresh NQ-2026 to be believed. Control = ordinary local high, same entry model.")
try:
    order=["NQ-9yr","NQ-2026","BTC","SOL"]; order=[a for a in order if a in CHART and CHART[a]]
    labs=["TOP control","TOP trio+confirm","TOP trio+confirm+late"]; x=np.arange(len(order)); w=0.26
    fig,ax=plt.subplots(figsize=(9,3.8))
    for k,(lab,col) in enumerate(zip(labs,[DOWN,MID,UP])):
        vals=[CHART[a].get(lab,{}).get("exp",np.nan) for a in order]
        ax.bar(x+(k-1)*w,vals,w,label=lab,color=col,edgecolor=EDGE)
    ax.axhline(0,color=EDGE,lw=1); ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("expectancy (R) — TOPS")
    ax.set_title("Stacked entry: does trio+confirm(+late) beat an ordinary local high? (0 = no edge)"); ax.legend()
    fig.tight_layout(); fig.savefig(OUT+"stacked_expectancy.png"); plt.close(fig)
except Exception as e: say(f"chart ERR {e}")
open(OUT+"STACKED.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved -> STACKED.md")
