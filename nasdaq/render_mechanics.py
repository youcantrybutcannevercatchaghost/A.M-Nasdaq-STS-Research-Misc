"""
Annotate the REAL 2026-06-02 NQ chart with the liquidity mechanic we discussed:
grab buy-side (30645) -> reverse to grab untapped sell-side (lower shelf/low) -> run to the DRAW (PDH).
Marks the entry + target + stop and the R. His colours. Saves a big PNG to the Desktop.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import pandas as pd, numpy as np
from datetime import time
SRC="DATA/chart-trainer/traindata.parquet"
OUT_DESK="DATA/NQ_2026-06-02_liquidity_mechanics.png"
OUT_FOLDER="DATA/market-explore/look/NQ_2026-06-02_mechanics.png"
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
DATE=pd.Timestamp("2026-06-02").date()
# levels
rth=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"),C=("c","last"))
dts=list(rth.index); pr=dts[dts.index(DATE)-1]
PDH=float(rth.loc[pr].H); PDL=float(rth.loc[pr].L); PDC=float(rth.loc[pr].C)
ds=pd.Timestamp(DATE).tz_localize("America/New_York")
def win(a0,b0,a1,b1,dd0=0,dd1=0):
    s=d[(d.index>=(ds+pd.Timedelta(days=dd0)).replace(hour=a0,minute=b0))&(d.index<(ds+pd.Timedelta(days=dd1)).replace(hour=a1,minute=b1))]
    return (float(s.h.max()),float(s.l.min())) if len(s) else (np.nan,np.nan)
PMH,PML=win(4,0,9,30); ASIAH,ASIAL=win(20,0,0,0,-1,0); LDNH,LDNL=win(2,0,5,0); ONH,ONL=win(18,0,9,30,-1,0)
# session bars 07:00-15:00
x=d[(d.date==DATE)&(d.t>=420)&(d.t<900)]
r=x.resample("5min").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).dropna().reset_index()
r["m"]=r["et"].dt.hour*60+r["et"].dt.minute
h=r.h.values;l=r.l.values;o=r.o.values;c=r.c.values;m=r.m.values;n=len(r)
def idxwin(a,b):
    w=np.where((m>=a)&(m<b))[0]; return w
# 1) morning buy-side high (09:30-11:00)
w=idxwin(570,660); hi=w[np.argmax(h[w])]
# 2) sell-side low after the high (to 12:30)
w2=np.where((np.arange(n)>hi)&(m<750))[0]; lo=w2[np.argmin(l[w2])]
# 3) entry = first close reclaim back above lower shelf (LDNL) after the low
shelf=max(LDNL,ASIAH,PDEQ if False else ASIAH); shelf=LDNL
en=None
for i in range(lo+1,n):
    if c[i]>shelf: en=i; break
# 4) PDH tap after the low
pt=None
for i in range(lo+1,n):
    if h[i]>=PDH: pt=i; break
entry=float(c[en]) if en is not None else float(c[lo]); stop=float(l[lo])-8; tgt=PDH
risk=entry-stop; rew=tgt-entry; RR=rew/risk if risk>0 else 0
print(f"high@{r.et[hi]:%H:%M} {h[hi]:.0f} | low@{r.et[lo]:%H:%M} {l[lo]:.0f} | entry@{r.et[en]:%H:%M} {entry:.0f} | PDHtap@{(r.et[pt] if pt else None)} | R {RR:.1f} reward {rew:.0f}pt")

fig,ax=plt.subplots(figsize=(17,9)); fig.set_facecolor(BG); ax.set_facecolor(BG)
for k in range(n):
    col=UP if c[k]>=o[k] else DOWN
    ax.add_patch(Rectangle((k-0.36,min(o[k],c[k])),0.72,abs(c[k]-o[k])+0.1,facecolor=col,edgecolor=EDGE,linewidth=.6,zorder=3))
    ax.plot([k,k],[l[k],h[k]],color=EDGE,linewidth=.7,zorder=2)
lv=[("PDH",PDH,"#c81e1e",2.2),("PMH/LDNH/ONH  (stack)",PMH,"#5b2a9b",1.2),("PDC",PDC,"#9a7d0a",1.0),
    ("LDNL",LDNL,"#b5651d",1.0),("ASIAH",ASIAH,"#1e7d32",1.0),("PML",PML,"#5b2a9b",1.0)]
for nm,val,cc,lw in lv:
    if np.isnan(val): continue
    ax.axhline(val,color=cc,lw=lw,ls="--",alpha=.8,zorder=1); ax.text(n+0.5,val,f"{nm} {val:.0f}",va="center",fontsize=9,color=cc,weight="bold")
# shelf band
ax.axhspan(min(PML,ASIAL if not np.isnan(ASIAL) else PML),LDNL,color="#1e5fc8",alpha=.06,zorder=0)
def note(k,price,txt,dy,dx=0,ha="center"):
    ax.annotate(txt,xy=(k,price),xytext=(k+dx,price+dy),ha=ha,fontsize=10,weight="bold",color=EDGE,
        bbox=dict(boxstyle="round,pad=0.35",fc="#ececec",ec=EDGE,lw=1),
        arrowprops=dict(arrowstyle="->",color=EDGE,lw=1.6),zorder=6)
rng=h.max()-l.min()
note(hi,h[hi],"① interim high 30647 — small pullback\n(NOT the top: PDH still untapped above)",dy=rng*0.06)
ax.add_patch(FancyArrowPatch((hi,h[hi]),(lo,l[lo]),connectionstyle="arc3,rad=-0.25",arrowstyle="-|>",mutation_scale=20,color="#555",lw=1.8,zorder=5))
note(lo,l[lo],"② the RETRACE — dips back below the stack to\nrebalance / grab liquidity = the ENTRY zone, not the top",dy=-rng*0.10)
if en is not None:
    ax.scatter([en],[entry],s=150,marker="^",color="#0a7d2c",edgecolor=EDGE,zorder=7)
    note(en,entry,f"③ ENTRY: buy the retrace (draw still untapped)\nstop {stop:.0f} · target PDH {PDH:.0f} · ~{RR:.1f}R ({rew:.0f} pt)",dy=-rng*0.17,dx=7)
if pt is not None:
    ax.add_patch(FancyArrowPatch((en if en else lo,entry),(pt,PDH),connectionstyle="arc3,rad=-0.15",arrowstyle="-|>",mutation_scale=24,color="#0a7d2c",lw=2.4,zorder=5))
    note(pt,PDH,f"④ runs to PDH — the untapped DRAW = the move (+{rew:.0f}pt)",dy=rng*0.03,dx=-4,ha="right")
ax.text(0.5,rng*0.0+l.min()-rng*0.02,"", fontsize=1)
ax.set_title("NQ  2026-06-02  —  while the DRAW (PDH) is untapped above, the PULLBACK is the ENTRY, not the top",
             color=EDGE,fontsize=13,weight="bold")
# framework box
ax.text(0.012,0.985,"THE READ (06-02):\n• PDH = the untapped DRAW above → bias is UP\n• while the draw is unfilled, PULLBACKS ARE ENTRIES,\n   not tops.  30647 wasn't the top — PDH still sat above.\n• the dip (②) rebalances / grabs liquidity → buy it (③)\n• target the draw (④).\n• 'Is this the top?' ≈ 'has the draw (PDH) been hit yet?'\n   Not yet → the dip is a buy.  Only once PDH is tapped\n   does the real top become likely.",
    transform=ax.transAxes,va="top",ha="left",fontsize=9.5,color=EDGE,
    bbox=dict(boxstyle="round,pad=0.5",fc="#e4e4e4",ec=EDGE,lw=1.2),zorder=8)
xt=[k for k in range(0,n,6)]; ax.set_xticks(xt); ax.set_xticklabels([f"{r.et[k]:%H:%M}" for k in xt],fontsize=8)
ax.set_xlim(-1,n+7); ax.set_ylim(l.min()-rng*.04,h.max()+rng*.05); ax.grid(True,color="#9a9a9a",lw=.3,alpha=.5)
[s.set_color(EDGE) for s in ax.spines.values()]; ax.tick_params(colors=EDGE)
fig.tight_layout()
for p in (OUT_DESK,OUT_FOLDER): fig.savefig(p,dpi=110,facecolor=BG)
plt.close(fig); print("saved ->",OUT_DESK)
