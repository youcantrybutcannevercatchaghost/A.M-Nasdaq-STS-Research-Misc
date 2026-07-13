"""
CONTACT SHEETS — many whole NQ days at a glance, to LOOK the way a trader flips the tape.
Each cell = one day, 07:00-16:00 ET, his colours, faint PDH/PDL/PDC. Title=date + range. No notes, cold.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd, numpy as np, os
SRC="DATA/chart-trainer/traindata.parquet"; OUT="DATA/market-explore/look/"; os.makedirs(OUT,exist_ok=True)
UP="#dbdbdb"; DOWN="#808080"; EDGE="#000000"; BG="#b8b8b8"
d=pd.read_parquet(SRC,columns=["ts","o","h","l","c"]); d["ts"]=pd.to_datetime(d.ts,utc=True)
d["et"]=d.ts.dt.tz_convert("America/New_York"); d=d.set_index("et").sort_index()
d["date"]=d.index.date; d["t"]=d.index.hour*60+d.index.minute
rth=d[(d.t>=570)&(d.t<960)].groupby("date").agg(H=("h","max"),L=("l","min"),C=("c","last"))
alldates=list(rth.index)
d26=[x for x in alldates if x.year==2026]

def cell(ax,date):
    i=alldates.index(date)
    x=d[(d.date==date)&(d.t>=420)&(d.t<960)]  # 07:00-16:00 ET
    r=x.resample("5min").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).dropna()
    if len(r)<10: ax.axis("off"); return
    for k,(t,row) in enumerate(r.iterrows()):
        col=UP if row.c>=row.o else DOWN
        ax.add_patch(Rectangle((k-0.4,min(row.o,row.c)),0.8,abs(row.c-row.o)+1e-6,facecolor=col,edgecolor=EDGE,linewidth=.25,zorder=3))
        ax.plot([k,k],[row.l,row.h],color=EDGE,linewidth=.3,zorder=2)
    if i>0:
        pr=rth.iloc[i-1]
        for lv,c2 in [(pr.H,"#333"),(pr.L,"#333"),(pr.C,"#555")]:
            ax.axhline(lv,color=c2,lw=.5,ls="--",alpha=.5,zorder=1)
    # mark 09:30
    for k,(t,_) in enumerate(r.iterrows()):
        if t.hour==9 and t.minute==30: ax.axvline(k,color=EDGE,lw=.5,alpha=.4); break
    rng=r.h.max()-r.l.min()
    ax.set_ylim(r.l.min()-rng*.05,r.h.max()+rng*.05); ax.set_xlim(-1,len(r))
    ax.set_title(f"{date}  ({rng:.0f}p)",fontsize=8,color=EDGE); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(EDGE)

def sheet(dates,name):
    n=len(dates); cols=5; rows=int(np.ceil(n/cols))
    fig,axes=plt.subplots(rows,cols,figsize=(cols*3.0,rows*2.1)); fig.set_facecolor(BG)
    axes=np.array(axes).reshape(-1)
    for a in axes: a.set_facecolor(BG)
    for k,dt in enumerate(dates): cell(axes[k],dt)
    for k in range(len(dates),len(axes)): axes[k].axis("off")
    fig.suptitle(f"NQ tape — {name}  (each cell 07:00-16:00 ET, dashed=PDH/PDL/PDC)",color=EDGE,fontsize=12)
    fig.tight_layout(rect=[0,0,1,0.98]); p=f"{OUT}sheet_{name}.png"; fig.savefig(p,dpi=100,facecolor=BG); plt.close(fig); print("saved",p)

sheet(d26[0:20],"2026_A")
sheet(d26[20:40],"2026_B")
sheet(d26[40:60],"2026_C")
print("total 2026 days:",len(d26))
