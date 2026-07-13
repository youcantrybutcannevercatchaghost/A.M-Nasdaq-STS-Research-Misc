"""
BACKTEST HIS READ: 'stacks + front-run reach and dump'.
Setup (SHORT): >=2 overnight/prior levels {PDH,ONH,PMH,AsiaH,LondonH} clustered within a band = a STACK above.
Price REACHES up and SWEEPS above the stack top, then REJECTS (closes back below within 3 bars) -> SHORT.
Stop = sweep high + buffer. Target = 2R. Mirror LONG on a downside stack {PDL,ONL,PML,AsiaL,LondonL}.
One trade/day (first trigger). 5m bars, RTH 09:30-15:00 trigger, manage to 16:00. Costs 2pt/trade.
Honest: report trades, win%, avg R, total pts, $ (MNQ $2/pt & NQ $20/pt), MFE (how far the dump ran), equity curve.
9yr(2017-25) vs FRESH 2026. No param-hunting.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np, sys
from datetime import time
sys.stdout.reconfigure(encoding="utf-8")
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/"
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"savefig.facecolor":BG,"axes.edgecolor":EDGE,
  "axes.labelcolor":EDGE,"text.color":EDGE,"xtick.color":EDGE,"ytick.color":EDGE,"axes.titlecolor":EDGE,"axes.grid":True,"grid.color":"#949494","grid.linewidth":.4})
R=["BACKTEST — 'stack + front-run reach & dump'. 5m, one trade/day, stop=sweep extreme, target 2R, 2pt cost.\n"]
def say(s): print(s); R.append(s)
BAND=0.0010; BUF=2.0; COST=2.0; REJECT=3
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
rth=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"),C=("c","last"))
dts=list(rth.index); prevmap={dts[i]:dts[i-1] for i in range(1,len(dts))}
def stack(levels, band_px):
    levels=sorted(levels)
    best=None
    for i in range(len(levels)):
        grp=[levels[i]]
        for j in range(i+1,len(levels)):
            if levels[j]-levels[i]<=band_px: grp.append(levels[j])
        if len(grp)>=2 and (best is None or len(grp)>len(best)): best=grp
    return best
def wlevels(date):
    ds=pd.Timestamp(date).tz_localize("America/New_York")
    def win(a0,b0,a1,b1,d0=0,d1=0):
        s=d[(d.index>=(ds+pd.Timedelta(days=d0)).replace(hour=a0,minute=b0))&(d.index<(ds+pd.Timedelta(days=d1)).replace(hour=a1,minute=b1))]
        return (s.h.max(),s.l.min()) if len(s) else (np.nan,np.nan)
    L={}
    pr=prevmap.get(date)
    if pr is not None: L["PDH"],L["PDL"]=rth.loc[pr].H,rth.loc[pr].L
    L["ONH"],L["ONL"]=win(18,0,9,30,-1,0); L["AsiaH"],L["AsiaL"]=win(20,0,0,0,-1,0)
    L["LDNH"],L["LDNL"]=win(2,0,5,0); L["PMH"],L["PML"]=win(4,0,9,30)
    return L
trades=[]
for date,g in d[(d.t>=570)&(d.t<960)].groupby("date"):
    r=g.resample("5min").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).dropna()
    if len(r)<40: continue
    L=wlevels(date); px=r.c.iloc[0]; band=px*BAND
    ups=[L[k] for k in ["PDH","ONH","PMH","AsiaH","LDNH"] if k in L and pd.notna(L[k]) and L[k]>px]
    dns=[L[k] for k in ["PDL","ONL","PML","AsiaL","LDNL"] if k in L and pd.notna(L[k]) and L[k]<px]
    us=stack(ups,band); ds_=stack(dns,band)
    h=r.h.values; l=r.l.values; c=r.c.values; n=len(r); trig=None
    ntrig=min(n-1, r.index.get_indexer([r.index[r.index.indexer_between_time("09:30","15:00")][-1]])[0] if len(r.index.indexer_between_time("09:30","15:00")) else n-1)
    for i in range(n):
        if r.index[i].hour*60+r.index[i].minute>900: break  # stop looking after 15:00
        if us is not None and trig is None:
            top=max(us)
            if h[i]>top:  # swept above the stack
                sweep_hi=h[i]
                for j in range(i,min(i+1+REJECT,n)):
                    sweep_hi=max(sweep_hi,h[j])
                    if c[j]<top:  # rejected back below
                        trig=("short",j,c[j],sweep_hi+BUF,len(us)); break
                if trig: break
        if ds_ is not None and trig is None:
            bot=min(ds_)
            if l[i]<bot:
                sweep_lo=l[i]
                for j in range(i,min(i+1+REJECT,n)):
                    sweep_lo=min(sweep_lo,l[j])
                    if c[j]>bot:
                        trig=("long",j,c[j],sweep_lo-BUF,len(ds_)); break
                if trig: break
    if trig is None: continue
    side,e,entry,stop,ss=trig; Rr=abs(stop-entry)
    if Rr<2: continue
    tgt=entry-2*Rr if side=="short" else entry+2*Rr
    outcome=None; mfe=0
    for k in range(e+1,n):
        if side=="short":
            mfe=max(mfe,entry-l[k])
            if h[k]>=stop: outcome=-1.0; exitpx=stop; break
            if l[k]<=tgt: outcome=2.0; exitpx=tgt; break
        else:
            mfe=max(mfe,h[k]-entry)
            if l[k]<=stop: outcome=-1.0; exitpx=stop; break
            if h[k]>=tgt: outcome=2.0; exitpx=tgt; break
    if outcome is None: exitpx=c[-1]; outcome=((entry-exitpx) if side=="short" else (exitpx-entry))/Rr
    pts=(entry-exitpx) if side=="short" else (exitpx-entry); pts-=COST
    trades.append(dict(date=date,yr=pd.Timestamp(date).year,side=side,R=outcome,pts=pts,Rr=Rr,mfe=mfe,stacksize=ss))
T=pd.DataFrame(trades)
def blk(T,tag):
    if not len(T): say(f"\n{tag}: no trades"); return
    tot=T.pts.sum(); say(f"\n===== {tag} — {len(T)} trades ({T.side.value_counts().to_dict()}) =====")
    say(f"  win% (2R b4 stop): {100*(T.R>0).mean():.0f} | avg R/trade (net-ish): {T.R.mean():+.2f} | expectancy pts/trade: {T.pts.mean():+.1f}")
    say(f"  TOTAL: {tot:+.0f} pts  =>  MNQ ${tot*2:+,.0f} (1 micro)  |  NQ ${tot*20:+,.0f} (1 mini)  [after {COST}pt cost/trade]")
    say(f"  the DUMP itself (MFE after sweep-reject): median {T.mfe.median():.0f} pts, p75 {T.mfe.quantile(.75):.0f} pts  <- is the move real even if mgmt is hard?")
blk(T,"9yr+2026 ALL"); blk(T[T.yr<=2025],"9yr 2017-2025"); blk(T[T.yr==2026],"FRESH 2026")
# equity
try:
    fig,ax=plt.subplots(figsize=(9,3.6)); Ts=T.sort_values("date")
    ax.plot(range(len(Ts)),Ts.pts.cumsum(),color=EDGE,lw=1.3)
    ax.axhline(0,color=DOWN,lw=1,ls="--"); ax.set_title("Stack front-run-reach-dump — cumulative points (net of cost)")
    ax.set_xlabel("trade #"); ax.set_ylabel("cum pts"); fig.tight_layout(); fig.savefig(OUT+"stack_equity.png"); plt.close(fig)
except Exception as e: say(f"chart {e}")
open(OUT+"BACKTEST_STACK.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved BACKTEST_STACK.md")
