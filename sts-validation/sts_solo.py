#!/usr/bin/env python3
"""STEP 1 — trade each STS sub STANDALONE (own account, no cross-blocking) on 9yr NQ + 2026.
Unmasks each sub's true edge from the portfolio's single-slot competition. Gauntlets each."""
import os, sys, pandas as pd, numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import sts_port as sp
from strategy_validator import validate
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

vix=pd.read_parquet("vix.parquet"); vix3m=pd.read_parquet("vix3m.parquet")
print("loading data...")
r9=sp.load5m("DATA/orb-research/data/nq_1m_9yr.parquet"); I9=sp.build(r9,vix,vix3m)
r26=sp.load5m("DATA/orb-research/data/nq_of_1m.parquet"); I26=sp.build(r26,vix,vix3m)
names={"S1":"Trend-long","S2":"Long-ORB","S3":"RSI-short","S4":"Short-ORB","S5":"Overnight","S6":"Universal"}
rows=[]; curves={}
for s in ["S1","S2","S3","S4","S5","S6"]:
    T=sp.run(r9,I9,f"{s} 9yr",only=s); T26=sp.run(r26,I26,f"{s} 26",only=s)
    if len(T)==0: continue
    net=T.pnl.sum(); win=100*(T.pnl>0).mean()
    pf=T.pnl[T.pnl>0].sum()/abs(T.pnl[T.pnl<0].sum()) if (T.pnl<0).any() else 99
    curve=T.pnl.cumsum(); mdd=(curve.cummax()-curve).max()
    curves[s]=(pd.to_datetime(T.entry_ts).values, curve.values)
    Rn=(T.pnl/T.pnl.abs().mean()).values
    verdict=validate([{"R":float(x),"entry_ts":ts} for x,ts in zip(Rn,T.entry_ts)], f"{s} {names[s]}")
    n26=T26.pnl.sum() if len(T26) else 0.0; w26=100*(T26.pnl>0).mean() if len(T26) else 0.0
    rows.append(dict(sub=s,name=names[s],n=len(T),net=net,pf=pf,win=win,mdd=mdd,verdict=verdict,net26=n26,win26=w26,n26=len(T26)))
SC=pd.DataFrame(rows); SC.to_parquet("sts_solo_scorecard.parquet")
print("\n\n"+"="*88)
print("  STANDALONE SCORECARD — each STS sub solo (no cross-blocking)")
print("="*88)
for r in SC.itertuples():
    print(f"  {r.sub} {r.name:11s} | 9yr: ${r.net/1000:+6.0f}k  PF {r.pf:4.2f}  win {r.win:3.0f}%  DD ${r.mdd/1000:4.0f}k  n{r.n:<5} [{r.verdict:8s}] | 2026: ${r.net26/1000:+5.0f}k win {r.win26:3.0f}% n{r.n26}")

# clean overlaid equity curves
BG="#0d1117";GRID="#21262d";TXT="#e6edf3";MUT="#8b949e"
cols={"S1":"#58a6ff","S2":"#2ea043","S3":"#d29922","S4":"#f85149","S5":"#a371f7","S6":"#39c5cf"}
fig,ax=plt.subplots(figsize=(12,7)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
fig.subplots_adjust(top=0.80,left=0.10,right=0.96,bottom=0.12)
for s in curves:
    x,y=curves[s]; ax.plot(x,y/1000,color=cols[s],lw=1.9,label=f"{s} {names[s]}")
ax.axhline(0,color=MUT,lw=1); ax.set_ylabel("cumulative net P&L  ($000s)")
for k in ["top","right"]: ax.spines[k].set_visible(False)
ax.spines["left"].set_color(GRID); ax.spines["bottom"].set_color(GRID)
ax.tick_params(colors=MUT); ax.grid(True,axis="y",alpha=.14)
ax.legend(facecolor=BG,edgecolor=GRID,labelcolor=TXT,loc="upper left",fontsize=10)
fig.text(0.10,0.925,"STS — each sub STANDALONE (no cross-blocking), 9yr NQ",color=TXT,fontsize=18,fontweight="bold")
fig.text(0.10,0.865,"The real per-sub edge, unmasked from the portfolio's single-slot competition.",color=MUT,fontsize=11.5)
fig.text(0.10,0.035,"Aston Monnach · standalone sub decomposition",color="#4d5866",fontsize=9)
fig.savefig("sts_solo_curves.png",dpi=140); import shutil; shutil.copy("sts_solo_curves.png","DATA/sts_solo_curves.png")
print("\nDONE — saved sts_solo_curves.png (Desktop) + sts_solo_scorecard.parquet")
