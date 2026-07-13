"""
STRUCTURAL FINGERPRINT OF THE DAILY TOP/BOTTOM (NQ 9yr RTH). Descriptive, look-ahead ok.
For every CONFIRMED daily high/low, what structure is there? -- and crucially, compared to an
ORDINARY swing high/low (control), so we see what's SPECIAL about the real turn vs common everywhere.
Features around the extreme + 15min after:
  - SWEPT a level? (pokes <=tol above PDH / PMH / ORH / prior swing-high, then reverses = stop-run)
  - STACKED levels? (# reference levels within a band)
  - FVG formed on the reversal? (bearish 3-bar gap in the 15min after a high)
  - BOS after? (broke the pre-high micro-swing-low within 15min = structure flipped)
  - VOLUME climax at the bar
Levels: PDH/PDL (prior RTH day), PMH/PML (premarket 04:00-09:30 ET), ORH/ORL (09:30-09:45), round-100, prior intraday swings.
report -> FINGERPRINT.md ; charts in his colours.
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
R=["STRUCTURAL FINGERPRINT OF THE DAILY TOP/BOTTOM — NQ 9yr. Day-extreme vs ordinary swing (control).\n"]
def say(s): print(s); R.append(s)

d=pd.read_parquet(FUT+"nq_1m_9yr.parquet",columns=["ts","o","h","l","c","v"])
d["ts"]=pd.to_datetime(d.ts,utc=True); d=d.sort_values("ts").reset_index(drop=True)
et=d.ts.dt.tz_convert("America/New_York"); d["et"]=et; d["date"]=et.dt.date
d["t"]=et.dt.hour*60+et.dt.minute; d["mfo"]=d.t-570
rthmask=(d.t>=570)&(d.t<960)
# per-date reference levels
rth=d[rthmask]; g=rth.groupby("date")
PDH=g.h.max(); PDL=g.l.min()
pm=d[(d.t>=240)&(d.t<570)].groupby("date"); PMH=pm.h.max(); PML=pm.l.min()
orr=d[(d.t>=570)&(d.t<585)].groupby("date"); ORH=orr.h.max(); ORL=orr.l.min()
dates=sorted(rth.date.unique()); prev={dates[i]:dates[i-1] for i in range(1,len(dates))}

def pivots_high(h,w=5):
    n=len(h); out=np.zeros(n,bool)
    for i in range(w,n-w):
        if h[i]==h[i-w:i+w+1].max(): out[i]=True
    return out
def pivots_low(l,w=5):
    n=len(l); out=np.zeros(n,bool)
    for i in range(w,n-w):
        if l[i]==l[i-w:i+w+1].min(): out[i]=True
    return out

rows=[]
for date,gg in rth.groupby("date"):
    if date not in prev: continue
    h=gg.h.values; l=gg.l.values; o=gg.o.values; c=gg.c.values; v=gg.v.values.astype(float); mfo=gg.mfo.values
    n=len(gg)
    if n<120: continue
    px=c.mean(); tol=px*0.0008; band=px*0.0015; vm=v.mean() or 1
    pdh=PDH.get(prev[date],np.nan); pdl=PDL.get(prev[date],np.nan)
    pmh=PMH.get(date,np.nan); pml=PML.get(date,np.nan); orh=ORH.get(date,np.nan); orl=ORL.get(date,np.nan)
    ph=pivots_high(h); pl=pivots_low(l)
    hi=int(h.argmax()); lo=int(l.argmin())
    def hi_levels(idx):  # resistance levels known at/before idx that sit below the bar's high
        L=[("PDH",pdh),("PMH",pmh)]
        if mfo[idx]>=15: L.append(("ORH",orh))
        L.append(("round",np.ceil(h[idx]/100)*100-100 if h[idx]%100 else h[idx]-100))
        prior=[h[j] for j in range(idx) if ph[j]]
        if prior: L.append(("swing",max([p for p in prior if p<=h[idx]]+[np.nan])))
        return [(nm,lv) for nm,lv in L if np.isfinite(lv)]
    def feat_high(idx):
        H=h[idx]; levs=hi_levels(idx)
        swept=[(nm,H-lv) for nm,lv in levs if 0<=H-lv<=tol]      # poked just above then this is a high
        stacked=sum(1 for nm,lv in levs if abs(H-lv)<=band)
        # FVG bearish in next 15
        fvg=False
        for k in range(idx+1,min(n,idx+16)):
            if k-2>=0 and h[k]<l[k-2]: fvg=True; break
        # BOS: broke pre-high micro swing low (min low of prior 15) within next 15
        sup=l[max(0,idx-15):idx].min() if idx>0 else l[idx]
        e=min(n,idx+16); bos=(l[idx+1:e].min()<sup) if e>idx+1 else False
        return dict(swept=len(swept)>0, swept_lvl=(swept[0][0] if swept else ""), poke=(swept[0][1] if swept else np.nan),
                    stacked=stacked, fvg=fvg, bos=bos, vol=v[idx]/vm)
    # day HIGH
    fh=feat_high(hi); fh.update(kind="DAYHIGH",date=date); rows.append(fh)
    # control swing highs (not the day high), cap 4/day
    sw=[j for j in range(15,n-15) if ph[j] and j!=hi]
    for j in sw[::max(1,len(sw)//4)][:4]:
        fj=feat_high(j); fj.update(kind="swing",date=date); rows.append(fj)

T=pd.DataFrame(rows)
dh=T[T.kind=="DAYHIGH"]; sw=T[T.kind=="swing"]
say(f"NQ RTH days analysed: {len(dh)} | control swing-highs: {len(sw)}\n")
say(f"{'feature':28}{'DAY HIGH':>12}{'ordinary swing':>16}   (is the real top special?)")
def line(nm,col,pct=True):
    a=dh[col].mean()*(100 if pct else 1); b=sw[col].mean()*(100 if pct else 1)
    say(f"{nm:28}{a:>11.0f}{'%' if pct else ' '}{b:>15.0f}{'%' if pct else ''}   {'<-- '+('MORE at tops' if a>b*1.15 else 'same-ish') }")
line("swept a level (poke<=tol)","swept")
say(f"{'stacked levels: mean #':28}{dh.stacked.mean():>11.2f} {sw.stacked.mean():>15.2f}")
say(f"{'  >=2 levels within band':28}{100*dh.stacked.ge(2).mean():>10.0f}% {100*sw.stacked.ge(2).mean():>14.0f}%")
line("FVG formed in next 15min","fvg")
line("BOS (broke pre-swing-low)","bos")
say(f"{'volume at the bar (x avg)':28}{dh.vol.median():>11.1f}x {sw.vol.median():>14.1f}x")
# which level gets swept
sc=dh[dh.swept].swept_lvl.value_counts(normalize=True)
say(f"\nOf day-highs that swept a level, WHICH one: "+" ".join(f"{k} {100*v:.0f}%" for k,v in sc.items()))
say(f"median poke above the swept level: {dh[dh.swept].poke.median():.1f} pts (small = clean stop-run)")
# combined fingerprint: how often do MULTIPLE marks co-occur at the day high
dh2=dh.assign(marks=dh.swept.astype(int)+dh.fvg.astype(int)+dh.bos.astype(int)+dh.stacked.ge(2).astype(int)+dh.vol.ge(1.5).astype(int))
say(f"\n# of 5 fingerprints present at the day HIGH (swept/stacked>=2/FVG/BOS/vol>=1.5x):")
say("  "+" ".join(f"{k}:{100*v:.0f}%" for k,v in dh2.marks.value_counts(normalize=True).sort_index().items()))
say(f"  >=3 of 5 present at the day high: {100*dh2.marks.ge(3).mean():.0f}%  (vs ordinary swing "
    f"{100*(sw.swept.astype(int)+sw.fvg.astype(int)+sw.bos.astype(int)+sw.stacked.ge(2).astype(int)+sw.vol.ge(1.5).astype(int)).ge(3).mean():.0f}%)")

# chart
try:
    feats=["swept","fvg","bos"]; labels=["swept a level","FVG in 15m after","BOS in 15m after"]
    dhv=[100*dh[f].mean() for f in feats]+[100*dh.stacked.ge(2).mean()]
    swv=[100*sw[f].mean() for f in feats]+[100*sw.stacked.ge(2).mean()]
    labels=labels+["stacked >=2"]
    x=np.arange(len(labels)); w=0.38
    fig,ax=plt.subplots(figsize=(8,3.6))
    ax.bar(x-w/2,dhv,w,label="DAY HIGH (real top)",color=UP,edgecolor=EDGE)
    ax.bar(x+w/2,swv,w,label="ordinary swing high",color=DOWN,edgecolor=EDGE)
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylabel("% of cases"); ax.legend()
    ax.set_title("NQ — structure at the REAL daily top vs an ordinary swing high")
    fig.tight_layout(); fig.savefig(OUT+"NQ_fingerprint.png"); plt.close(fig)
except Exception as e: say(f"chart ERR {e}")
open(OUT+"FINGERPRINT.md","w",encoding="utf-8").write("\n".join(R)); print("\nsaved -> FINGERPRINT.md")
