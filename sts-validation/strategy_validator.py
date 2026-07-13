#!/usr/bin/env python3
"""
====================================================================
  STRATEGY VALIDATOR
  By Aston Monnach

  © Aston Monnach.
====================================================================

Feed it a strategy's trades (each with an 'R' multiple and an 'entry_ts') and it runs
the full statistical gauntlet, printing a PASS / CONCERNS / FAIL verdict with reasons.

    trades = [{"R": 1.5, "entry_ts": "2025-03-04T14:30:00"}, ...]
    #  R = realised profit in units of the trade's initial risk
    #  entry_ts = ISO-8601 timestamp

Checks: sample size | edge (win/PF/expectancy) | tail-dependence | out-of-sample split |
significance (per-trade AND day-level) | max drawdown | longest losing run | risk of ruin.

NOTE: the execution-realism half (next-bar-open fills, known-before-bar stops, real fees,
vs buy-and-hold) needs the strategy's own code + data, so it stays per-strategy
(cross-check any candidate against a known-good trade list).
"""
import json, sys, numpy as np, random
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
random.seed(0)

BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║   STRATEGY VALIDATOR                                 ║
║   by Aston Monnach                         ║
║                   ║
╚══════════════════════════════════════════════════════════════════╝"""

def validate(trades, label, risk_pct=1.0):
    trades = sorted(trades, key=lambda t: t["entry_ts"])
    R = np.array([float(t["R"]) for t in trades]); n = len(R)
    days = sorted({str(t["entry_ts"])[:10] for t in trades})
    flags = []
    print(f"\n{'═'*66}\n  VALIDATION REPORT  —  {label}\n{'═'*66}")

    ok = n >= 100
    print(f"  [1] Sample size        n={n} trades, {len(days)} days      {'PASS' if ok else 'THIN — noise risk'}")
    if not ok: flags.append("thin sample")

    win=100*(R>0).mean(); pf=R[R>0].sum()/abs(R[R<0].sum()) if (R<0).any() else 99
    exp=R.mean(); print(f"  [2] Edge               win {win:.0f}%   PF {pf:.2f}   exp {exp:+.3f}R   sumR {R.sum():+.1f}")

    s=np.sort(R); mt3=R.sum()-s[-3:].sum(); mt5=R.sum()-s[-5:].sum()
    ok=mt3>0; print(f"  [3] Tail check         minus top-3 = {mt3:+.1f}R   minus top-5 = {mt5:+.1f}R   {'PASS' if ok else 'FRAGILE — rides a few winners'}")
    if not ok: flags.append("tail-dependent")

    cut=int(n*0.6); ISr=R[:cut]; OOSr=R[cut:]
    def pf_(x): return x[x>0].sum()/abs(x[x<0].sum()) if (x<0).any() and x[x<0].sum()!=0 else 99
    ispf,oospf=pf_(ISr),pf_(OOSr)
    ok = oospf>=1.0 and OOSr.mean()>0
    print(f"  [4] Out-of-sample      IS PF {ispf:.2f} (exp {ISr.mean():+.2f}R)  →  OOS PF {oospf:.2f} (exp {OOSr.mean():+.2f}R)   {'PASS' if ok else 'FAILS — collapses OOS'}")
    if not ok: flags.append("OOS collapse")

    t_trade = exp/(R.std(ddof=1)/np.sqrt(n)) if R.std()>0 else 0
    byday={}
    for tr in trades: byday.setdefault(str(tr["entry_ts"])[:10],[]).append(float(tr["R"]))
    dayR=np.array([sum(v) for v in byday.values()])
    t_day = dayR.mean()/(dayR.std(ddof=1)/np.sqrt(len(dayR))) if dayR.std()>0 else 0
    lo=dayR.mean()-1.96*dayR.std(ddof=1)/np.sqrt(len(dayR)); hi=dayR.mean()+1.96*dayR.std(ddof=1)/np.sqrt(len(dayR))
    ok=t_day>2.0 and lo>0
    print(f"  [5] Significance       per-trade t={t_trade:.2f} | DAY-level t={t_day:.2f}, 95%CI [{lo:+.2f},{hi:+.2f}]R/day   {'PASS' if ok else 'WEAK — CI includes ~0'}")
    if not ok: flags.append("not significant (day-level)")

    eq=np.cumsum(R); peak=np.maximum.accumulate(eq); maxdd=(peak-eq).max()
    print(f"  [6] Max drawdown       {maxdd:.1f}R   (peak-to-trough, at flat 1R/trade)")

    m=c=0
    for r in R:
        c=c+1 if r<0 else 0; m=max(m,c)
    print(f"  [7] Longest losing run {m} trades")

    ruin=0; sims=3000
    for _ in range(sims):
        e=1.0
        for _ in range(n):
            e*=(1+R[random.randrange(n)]*(risk_pct/100))
            if e<=0.5: ruin+=1; break
    ror=100*ruin/sims
    print(f"  [8] Risk of ruin       {ror:.1f}%   (illustrative: normalized-R @ {risk_pct}%/trade, NOT calibrated to real contract sizing)")

    verdict = "FAIL" if any(f in ("OOS collapse","not significant (day-level)") for f in flags) else ("CONCERNS" if flags else "PASS")
    print(f"{'─'*66}\n  VERDICT: {verdict}" + (f"   ⚠ {', '.join(flags)}" if flags else "   ✓ clean") + f"\n{'═'*66}")
    return verdict

if __name__=="__main__":
    print(BANNER)
    try:
        data=json.load(open("rd_trades.json"))
        for sym in ("SOL","BTC"):
            tr=[t for t in data.get(sym,[]) if "R" in t and "entry_ts" in t]
            if tr: validate(tr, f"DEMO: Range-Deviation · {sym} 15m")
    except FileNotFoundError:
        print("\n  (no demo data found — pass your own trade list to validate())")
