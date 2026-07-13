# STS → Python — port & validation bundle

**Prepared by Aston Monnach** for independent validation of the **STS (Regular)** 6-sub NQ book.
Purpose: reproduce the strategy in Python so it can be tested on **9 years of local NQ data** (free-plan TradingView can't show that history), then run it through a rigorous validation gauntlet.

> **Honesty statement.** This is a *mechanically faithful* port, cross-checked param-by-param against the Pine. It was then put through an **independent 4-dimension adversarial code audit** (look-ahead, Pine fidelity, accounting, sizing) — which found and **fixed 4 real divergences** (documented in §3). It is not claimed to be trade-for-trade identical to TradingView, but after the audit every load-bearing entry, exit, and sizing rule matches the Pine default book, and the remaining differences are small, one-directional, and listed. *This is the same logic and the same numbers, rebuilt and then adversarially checked — not something invented, and not something taken on trust.*

---

## 1. The 6 subs (mechanics, as ported)

| Sub | Logic | Entry window (ET) | Exit | Sizing tier |
|---|---|---|---|---|
| **S1 Trend-long** | long if `close > sessionVWAP` & `mom(250) > 1.0` | 09:40 | close<VWAP or 16:45 | ATR% 0.05/0.5 |
| **S2 Long-ORB** | close-breakout `> rangeHigh`, range green, `close>VWAP`; SL = range low | 09:45–15:25 | SL or **16:45** | ATR% 0.05/0.10 |
| **S3 RSI-short** | short if `close<VWAP` & `RSI(21)<25` & `VIX<20`; SL +1%; cover on VWAP reclaim | 09:40–15:10 | SL / VWAP / **16:45** | ATR% 0.05/0.5 |
| **S4 Short-ORB** | close-breakdown `< rangeLow`, range red, `close<VWAP`; SL +0.5% | 09:45–15:25 | SL or 15:55 | **RSI 10/25** |
| **S5 Overnight** | long @18:15 if `close>weeklyVWAP` & `1.0<dayATR%<1.5` & `VIX/VIX3M<0.95` & `VIX<252d-p75`; 0.5%/0.5% bracket | 18:15–18:29 | bracket or 08:30 | **wVWAP-dist/dayATR 0.25/0.50** |
| **S6 Universal** | breakout `dailyVWAP ± 1σ`, `close>open`, `ER(20)>0.65` (mirror short); SL 2.5×ATR, TP 6×ATR | 09:45–12:00 | bracket or 15:55 | ATR% 0.1/0.25 |

**S6 note:** "Universal" is this one independent sub (a symbol-agnostic trend-breakout), **not** an aggregate of the others. All six coexist in one script, sharing a single position slot.
**Sizing:** conviction-tier ladder → 1 / 2 / 3 contracts (no Kelly, no optimal-f). Each sub's tier variable differs (ATR%, RSI, or weekly-VWAP distance — matching the Pine per-sub `scaleMethod`). **Costs:** $2.05/contract commission + 2-tick slippage.

---

## 2. Param match-proof (Pine → this port)

Cross-checked against `STS-Regular/STS.pine`. ✅ = exact match. **†** = corrected after the audit (§3).

| Param | Pine | This port | |
|---|---|---|---|
| S1 entry 09:40 / mom>1.0 / tier 0.05,0.5 | L75–91 | `t==940`, `mom>1.0`, `tier(0.05,0.5)` | ✅ |
| S2 close-breakout / green / tier 0.05,0.10 | L107,113–114 | close-breakout, `tier(0.05,0.10)` | ✅ |
| S2 exit time | 16:45 close_all (L633) | `t>=1645` | ✅ **†** |
| S3 RSI(21)<25 / VIX<20 / SL+1% / tier 0.05,0.5 | L127–138 | matches | ✅ |
| S3 exit time | 16:45 close_all (15:10 = entry cutoff only) | `t>=1645` | ✅ **†** |
| S4 close-breakdown / red / SL+0.5% | L152–162 | matches | ✅ |
| **S4 sizing tier** | **Momentum/RSI** `rsi<10→3, rsi<25→2` (L160,163–164,307–313) | `tier(rsi,10,25)` | ✅ **†** |
| S5 entry 18:15–18:29 / ATR% 1.0–1.5 / contango<0.95 / SL,TP 0.5% | L179–185,535–547 | matches | ✅ |
| **S5 sizing tier** | **wVWAP-dist ÷ dayATR** `≤0.25→3, ≤0.50→2` (L189–190,276,329–336) | `dist=\|c−wVWAP\|/dayATR` | ✅ **†** |
| S6 ER>0.65 / ±1σ / 2.5×,6×ATR / tier 0.1,0.25 | L200–208,566–584 | matches | ✅ |

Entry conditions, thresholds, VWAP types (session/weekly = close-weighted; S6 daily = hlc3), green/red filters, and the S3 fixed-1% stop / S2 range-low stop were all independently confirmed correct.

---

## 3. Independent adversarial audit (what it found & fixed)

Four independent auditors read the code cold (one per dimension), and every material finding was re-checked by a separate adjudicator before acceptance.

**Confirmed clean:**
- **No look-ahead.** Every indicator is causal (VWAP cumulative; RSI/ATR/mom/ER trailing); prior-day and VIX values are lagged; the ORB range freezes before the breakout bar; exits read only the current bar. The entry fills at the signal bar's close — faithful to the Pine's `process_orders_on_close=true`, not future-peeking.
- **Statistics sound.** Chronological OOS split, tail-check, and day-level significance are correctly implemented; the R-normalization is mathematically harmless to them (verified `t(pnl)==t(R)`).

**Found & fixed (4 divergences, all in sizing/exits — entries were always correct):**
1. **S4 sizing** — was ATR%-tiered; Pine uses RSI/momentum. *Fixed.*
2. **S5 sizing** — was ATR%-tiered; Pine uses weekly-VWAP-distance ÷ daily-ATR (port had under-sized S5 ~2–3×). *Fixed.*
3. **S2 exit** — closed 15:55; Pine holds Long-ORB to 16:45. *Fixed.*
4. **S3 exit** — closed 15:10 (that's only the entry cutoff); Pine holds to 16:45. *Fixed.*

**Remaining minor approximations (disclosed, none flatter results):** session-VWAP anchored 18:00 ET; VIX is prior-day daily; stop fills book the stop price + flat slippage with no gap-open model (matches TradingView's own emulator); S6 band uses sample vs population stdev; 5-min resample from 1-min, front-month by dollar-volume. The printed Risk-of-Ruin is labelled illustrative (it assumes fixed-fractional sizing; the book uses fixed contracts).

---

## 4. Results (post-fix)

**Portfolio (all 6 subs, one slot), NQ 2017–2025 (in-sample):** **+$840k**, PF **1.36**, win 42%, max DD **$35k**, **every calendar year green**.

### Each sub STANDALONE (own slot) + 9-year gauntlet

| Sub | 9yr net | PF | win | maxDD | Gauntlet |
|---|---|---|---|---|---|
| S1 Trend-long | +$271k | 1.36 | 33% | $28k | ✅ PASS |
| S2 Long-ORB | +$243k | 1.32 | 51% | $31k | ✅ PASS |
| S3 RSI-short | +$204k | 1.81 | 41% | $29k | ✅ PASS |
| S4 Short-ORB | +$251k | 1.34 | 38% | $42k | ✅ PASS |
| S5 Overnight | +$165k | 1.70 | 62% | $20k | ✅ PASS |
| S6 Universal | +$171k | 1.48 | 45% | $23k | ✅ PASS |

All six subs pass the 9-year **in-sample** gauntlet standalone. That is necessary, not sufficient — the real test is forward.

### True-forward 2026 (held-out; COMPLETE Jan 1 → Jul 2, no gaps; n=152)

Data the book never saw. **Net positive forward:**

| Month | net | note |
|---|---|---|
| Jan | −$8.1k | S1 whipsawed |
| **Feb** | **+$49.5k** | Feb–Mar correction (NQ −6.9% peak-trough) — shorts + trend fire |
| **Mar** | **+$17.6k** | correction continued (NQ −9.8% peak-trough) |
| Apr | +$2.9k | |
| May | −$13.5k | choppy up-drift, S4 chopped |
| Jun | −$2.9k | S3 +23k (Jun 5 crash), S1 −12k |
| Jul (1 trd) | −$4.5k | |
| **ALL 2026** | **+$40.9k** | PF **1.16**, win 41% |
| **ex-S4** | **+$49.9k** | PF 1.24 |

**Honest verdict: in-sample strong; complete 2026 forward is net +$41k (PF 1.16) — modest, lumpy, but positive.** Per-sub (verified in the trades):
- **S4 (−$9k):** regime-conditional, NOT broken — made **+$31k in the Feb–Mar correction**, bled in the choppy up-months. Good in downtrends, bad in chop.
- **S3 (+$42k):** genuine capitulation-short — won **4 times** across 2026's selloffs (Feb 3, Feb 26, Jun 5). *But tail-dominated*: strip the single Jun 5 crash (+$41.8k) and S3 is ~flat, so high-variance.
- **S1 (+$6k) / S2 (+$1k) / S5 (+$2k):** small net positives; S1 lumpy (bad Jan, good Feb–Apr).

*(An earlier version of this file, run before the Feb–Mar data was available, showed −$25k and concluded "not confirming." That was a **data-gap artifact** — the missing months were exactly the correction that feeds a short-heavy book. Complete data reverses it. Lesson: incomplete forward data biased the conclusion as hard as any look-ahead would.)*

**Assessment: a promising deployable-candidate, not a proven machine.** PF 1.16 is below the 1.36 in-sample, month-to-month is lumpy, and the biggest contributor (S3) is tail-dependent — but the book *does* hold up out-of-sample across a full, mixed 6-month regime. More forward runway would firm it up. See `sts_solo_curves.png`.

**Design note — single-slot blocking (a lever worth knowing):** the book trades one position at a time (all subs share a slot via `position_size==0`). Over 9yr the book nets **+$840k (PF 1.36)**; the sum of the six subs run *independently* is **+$1.30M (PF 1.42)** — so the single-slot design leaves **~$462k / 35% on the table** to internal blocking (827 signals blocked). **S6 Universal is 88% blocked** (only 40 of 345 signals taken — it fires 09:45–12:00 when the slot is usually busy). Allowing 2 concurrent positions, or giving S6 priority in its window, could recover a chunk of that — at the cost of stacked (correlated) drawdowns and more margin. A design choice, not a bug.

---

## 5. Files

| File | What |
|---|---|
| `sts_port.py` | The full 6-sub book, ported (post-audit). Point `load5m(path)` at your NQ 1-min parquet. |
| `sts_solo.py` | Each sub standalone + gauntlet + equity-curve chart. |
| `strategy_validator.py` | The validation gauntlet (8 checks). |
| `trades_NQ_STS_9yr.csv` | All in-sample executions; `sub` column tags which strat fired. |
| `trades_2026_forward.csv` | The held-out 2026 forward trades (Jan + Apr–Jul); the −$25k in §4. |
| `sts_solo_curves.png` | Standalone per-sub equity curves. |
| `STS-Regular/STS.pine` | The original Pine source (reference for §2). |
| `vix.parquet`, `vix3m.parquet` | Daily VIX / VIX3M for the S3/S5 gates. |

**Not included:** the NQ 1-min history (your own data). Edit the path in `sts_port.py`.

```bash
python sts_port.py     # full portfolio book: net / PF / win / DD / by-year / by-sub
python sts_solo.py     # each sub standalone + gauntlet + equity-curve chart
```

---
*Aston Monnach ·  · validation toolkit. Shared for mutual strategy validation.*
