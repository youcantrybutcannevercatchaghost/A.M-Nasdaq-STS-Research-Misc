"""
RENDER real NQ candles in his colours with the LIQUIDITY MAP drawn (PDH/PDL/PDC/PDEQ, Asia H/L,
London H/L, PMH/PML, ON H/L) + FVGs — so I can LOOK the way he looks. No outcome labels: read it cold.
Window 02:00-16:00 ET, 5m. Saves PNGs to market-explore/look/.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd, numpy as np, os
from datetime import time
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/look/"; os.makedirs(OUT,exist_ok=True)
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c","v"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
rth=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"),C=("c","last"))
dates=list(rth.index)

def resample(x,rule):
    r=x.resample(rule).agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).dropna()
    return r

def levels(date):
    i=dates.index(date) if date in dates else None
    L={}
    if i and i>0:
        pr=rth.iloc[i-1]; L["PDH"]=pr.H; L["PDL"]=pr.L; L["PDC"]=pr.C; L["PDEQ"]=(pr.H+pr.L)/2
    ds=pd.Timestamp(date).tz_localize("America/New_York")
    def win(a0,b0,a1,b1,d0=0,d1=0):
        s=d[(d.index>= (ds+pd.Timedelta(days=d0)).replace(hour=a0,minute=b0)) &
             (d.index<  (ds+pd.Timedelta(days=d1)).replace(hour=a1,minute=b1))]
        return (s.h.max(),s.l.min()) if len(s) else (np.nan,np.nan)
    L["ONH"],L["ONL"]=win(18,0,9,30,d0=-1,d1=0)
    L["AsiaH"],L["AsiaL"]=win(20,0,0,0,d0=-1,d1=0)
    L["LDNH"],L["LDNL"]=win(2,0,5,0)
    L["PMH"],L["PML"]=win(4,0,9,30)
    return {k:v for k,v in L.items() if pd.notna(v)}

def fvgs(r):  # on the shown TF
    out=[]; h=r.h.values; l=r.l.values; idx=r.index
    for i in range(2,len(r)):
        if l[i]>h[i-2]: out.append(("bull",idx[i-2],h[i-2],l[i]))
        elif h[i]<l[i-2]: out.append(("bear",idx[i-2],h[i],l[i-2]))
    return out

def draw(date, rule="5min", tag="5m"):
    x=d[(d.date==date)&(d.t>=120)&(d.t<960)]  # 02:00-16:00 ET
    if len(x)<30: return None
    r=resample(x,rule)
    fig,ax=plt.subplots(figsize=(15,7)); ax.set_facecolor(BG); fig.set_facecolor(BG)
    xs=np.arange(len(r)); wpx=0.6
    for k,(t,row) in enumerate(r.iterrows()):
        col=UP if row.c>=row.o else DOWN
        ax.add_patch(Rectangle((k-wpx/2,min(row.o,row.c)),wpx,abs(row.c-row.o)+1e-6,facecolor=col,edgecolor=EDGE,linewidth=.6,zorder=3))
        ax.plot([k,k],[row.l,row.h],color=EDGE,linewidth=.6,zorder=2)
    # liquidity levels
    L=levels(date)
    for name,lv in L.items():
        ax.axhline(lv,color=EDGE,lw=0.8,ls="--",alpha=.55,zorder=1)
        ax.text(len(r)+0.5,lv,name,va="center",fontsize=8,color=EDGE)
    # FVGs (shown TF), only reasonably sized
    rng=r.h.max()-r.l.min()
    for typ,t0,lo,hi in fvgs(r):
        if hi-lo< rng*0.004: continue
        k0=r.index.get_loc(t0)
        ax.add_patch(Rectangle((k0-0.5,lo),len(r)-k0+0.5,hi-lo,facecolor="#000000" if typ=="bear" else "#ffffff",alpha=.10,edgecolor="none",zorder=1))
    # 09:30 open marker
    for k,(t,_) in enumerate(r.iterrows()):
        if t.hour==9 and t.minute==30: ax.axvline(k,color=EDGE,lw=1.0,alpha=.5); ax.text(k,r.h.max(),"09:30",fontsize=8,rotation=90,va="top"); break
    ax.set_xlim(-1,len(r)+8); ax.set_ylim(r.l.min()-rng*.03,r.h.max()+rng*.03)
    ax.set_title(f"NQ {date} — {tag}  (02:00-16:00 ET)  |  dashed = liquidity pools, shaded = FVG",color=EDGE)
    ax.grid(True,color="#9a9a9a",lw=.3,alpha=.5); [s.set_color(EDGE) for s in ax.spines.values()]
    ax.tick_params(colors=EDGE)
    fig.tight_layout(); p=f"{OUT}{date}_{tag}.png"; fig.savefig(p,dpi=95); plt.close(fig); return p

import datetime as dt
want=[dt.date(2026,1,2),dt.date(2026,1,5),dt.date(2026,1,6),dt.date(2026,1,7),dt.date(2026,6,15)]
for D in want:
    for rule,tag in [("5min","5m"),("15min","15m")]:
        p=draw(D,rule,tag)
        if p: print("saved",p)
print("done")
