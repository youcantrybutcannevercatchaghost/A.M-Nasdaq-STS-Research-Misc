"""Render specific pullback-to-draw trades so I can EYEBALL whether the logic is right.
Draws the RTH 5m day, PDH/PDL, and the trade's entry/stop/target/exit exactly as the backtest logged them."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd, numpy as np
from datetime import time
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/look/"
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
T=pd.read_csv(OUT.replace("look/","")+"draw_trades.csv")
import datetime as dt
def render(datestr):
    row=T[T.date==datestr].iloc[0]
    D=dt.date.fromisoformat(datestr)
    g=d[(d.date==D)&(d.t>=570)&(d.t<960)]
    r=g.resample("5min").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).dropna().reset_index()
    o=r.o.values;h=r.h.values;l=r.l.values;c=r.c.values;n=len(r)
    fig,ax=plt.subplots(figsize=(13,6.5)); fig.set_facecolor(BG); ax.set_facecolor(BG)
    for k in range(n):
        col=UP if c[k]>=o[k] else DOWN
        ax.add_patch(Rectangle((k-0.36,min(o[k],c[k])),0.72,abs(c[k]-o[k])+0.1,facecolor=col,edgecolor=EDGE,linewidth=.6,zorder=3))
        ax.plot([k,k],[l[k],h[k]],color=EDGE,linewidth=.7,zorder=2)
    e=int(row.ebar); x=int(row.xbar); side=row.side
    ax.axhline(row.target,color="#0a7d2c",lw=1.8,ls="--",zorder=1); ax.text(n+0.3,row.target,f"TARGET {row.target:.0f} ({'PDH' if side=='long' else 'PDL'})",color="#0a7d2c",fontsize=9,weight="bold",va="center")
    ax.axhline(row.stop,color="#c81e1e",lw=1.4,ls="--",zorder=1); ax.text(n+0.3,row.stop,f"STOP {row.stop:.0f}",color="#c81e1e",fontsize=9,va="center")
    ax.axhline(row.entry,color=EDGE,lw=1.2,zorder=1); ax.text(n+0.3,row.entry,f"ENTRY {row.entry:.0f}",color=EDGE,fontsize=9,va="center")
    mk="^" if side=="long" else "v"; ec="#0a7d2c" if side=="long" else "#c81e1e"
    ax.scatter([e],[row.entry],s=180,marker=mk,color=ec,edgecolor=EDGE,zorder=7)
    ax.scatter([x],[row.exit],s=150,marker="x",color="#000",linewidths=2.5,zorder=7)
    ax.annotate("ENTRY",(e,row.entry),xytext=(e-4,row.entry),fontsize=9,weight="bold",va="center",ha="right",color=ec)
    ax.annotate(f"EXIT ({row.result})",(x,row.exit),xytext=(x+2,row.exit),fontsize=9,weight="bold",va="center",color=EDGE)
    rng=h.max()-l.min()
    ax.set_title(f"{datestr}  {side.upper()} → {row.result.upper()}  {row.pts:+.0f}pt ({row.R:+.1f}R)   entry {row.entry_time}  [verify: entry after a pullback, target=the draw]",fontsize=11,weight="bold",color=EDGE)
    xt=list(range(0,n,6)); ax.set_xticks(xt); ax.set_xticklabels([f"{r.et[k]:%H:%M}" for k in xt],fontsize=8)
    ax.set_xlim(-1,n+9); ax.set_ylim(min(l.min(),row.stop)-rng*.04,max(h.max(),row.target)+rng*.04)
    ax.grid(True,color="#9a9a9a",lw=.3,alpha=.5); [s.set_color(EDGE) for s in ax.spines.values()]; ax.tick_params(colors=EDGE)
    fig.tight_layout(); p=f"{OUT}trade_{datestr}.png"; fig.savefig(p,dpi=100,facecolor=BG); plt.close(fig); print("saved",p)
for ds in ["2026-01-02","2026-01-09","2026-01-19","2026-01-14"]:
    try: render(ds)
    except Exception as ex: print(ds,"ERR",ex)
