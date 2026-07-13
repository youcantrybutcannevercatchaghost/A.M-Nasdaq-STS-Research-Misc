# The 6-Sub NQ Book — Strategy Reference

Private working reference. Rules as verified in the audited Python port (matches the Pine default book), plus the **regime character** each sub showed across the 9-year dissection.

**Global rules**
- **Instrument:** E-mini NQ ($20/point = $5/tick). **One position at a time** — all six subs share a single slot; the first to fire on a bar takes it.
- **Sizing:** conviction-tier ladder → **1 / 2 / 3 contracts** (no Kelly). Each sub's tier is decided by a different variable (below).
- **Costs modelled:** $2.05/contract commission (both sides) + 2-tick slippage. **Account:** $100k. **Bars:** 5-minute, ET. Session VWAP anchored 18:00 ET.

| Sub | Type | Direction | Session window (ET) | 9yr net (standalone) | Works best in |
|---|---|---|---|---|---|
| **S1** Trend-long | Momentum | Long | 09:40 | +$271k | UP-trend |
| **S2** Long-ORB | Breakout | Long | 09:45–15:25 | +$243k | UP-trend / range |
| **S3** RSI-short | Mean-reversion / capitulation | Short | 09:40–15:10 | +$204k | DOWN-trend, normal vol |
| **S4** Short-ORB | Breakdown | Short | 09:45–15:25 | +$251k | DOWN-trend |
| **S5** Overnight | Overnight drift | Long | 18:15–18:29 | +$165k | all-weather (smoothest) |
| **S6** Universal | Trend-breakout | Long + Short | 09:45–12:00 | +$171k | all-weather (bidirectional) |

---

## S1 · Trend-long
- **Entry (09:40 only):** `close > session VWAP` **and** `momentum(250 bars) > 1.0` (price rising vs 250 bars ago).
- **Stop:** none (no hard stop).
- **Exit:** `close < VWAP`, or the 16:45 close-all.
- **Sizing:** low-volatility ATR% tier (ATR% < 0.05 → 3 contracts, < 0.5 → 2, else 1).
- **Character:** the book's steadiest riser. Low win rate (**33%**) / high reward (RR **2.8**) — funds many small losses with big runners. **UP-trend engine** (+$174k in up-regimes); whipsaws in chop. Winners entered with clearly stronger momentum than losers.

## S2 · Long-ORB
- **Entry (09:45–15:25):** opening range = 09:30–09:45. Go long when `close` breaks **above** the range high, the range was **green** (`close > open`), and `close > VWAP`.
- **Stop:** range low (floored at entry × 0.99). **No target.**
- **Exit:** stop or the 16:45 close-all.
- **Sizing:** low-vol ATR% tier (0.05 / 0.10).
- **Character:** 51% win, RR 1.3. Winners and losers look identical at entry → an **unfilterable clean edge** (pure positive-expectancy). Strong in UP (+$194k), **loses in DOWN (−$28k)** — a long breakout fighting a downtrend.

## S3 · RSI-short
- **Entry (09:40–15:10):** `close < VWAP` **and** `RSI(21) < 25` **and** `VIX < 20`.
- **Stop:** +1% (entry × 1.01).
- **Exit:** VWAP reclaim (`close > VWAP`), or 16:45 close-all.
- **Sizing:** low-vol ATR% tier (0.05 / 0.5).
- **Character:** highest quality by PF (**1.81**). A **capitulation short** — it shorts oversold-below-VWAP and rides continuation. **DOWN-trend engine** (+$218k in down-regimes, PF 4.4, 58% win); **loses in UP (−$47k)** and gets squeezed in **high-VIX stress (−$15k, 11% win)** — the one clean filter candidate is tightening its VIX gate. Lumpy realisation (feast on selloffs, bleed between).

## S4 · Short-ORB
- **Entry (09:45–15:25):** go short when `close` breaks **below** the opening-range low, the range was **red** (`close < open`), and `close < VWAP`.
- **Stop:** +0.5% (entry × 1.005). **No target.**
- **Exit:** stop or 15:55 close.
- **Sizing:** **momentum / RSI tier** (RSI < 10 → 3 contracts, RSI < 25 → 2, else 1) — *not* ATR%.
- **Character:** biggest winners (RR up to 2.0). **DOWN-trend engine** (+$318k in down-regimes) but **loses hardest in UP (−$74k)** — shorting breakdowns into an uptrend. Its 2026 forward loss was this exact mechanism (a +25% up-year); it recovered +$31k in the Feb–Mar correction. Widest drawdown of the book ($42k standalone).

## S5 · Overnight
- **Entry (18:15–18:29):** `close > weekly VWAP` **and** `1.0 < prior-day ATR% < 1.5` **and** `VIX / VIX3M < 0.95` (contango) **and** `VIX < 252-day 75th percentile`.
- **Stop / Target:** 0.5% / 0.5% bracket.
- **Exit:** bracket, or ~08:30 the next morning.
- **Sizing:** **weekly-VWAP-distance ÷ daily-ATR** tier (≤ 0.25 → 3, ≤ 0.50 → 2, else 1).
- **Character:** highest win rate (**62%**), smoothest curve (max DD only $20k). Tight symmetric bracket; losers are clean stops, not given-back winners. **All-weather** — positive in up, down and range. The book's diversifier.

## S6 · Universal
- **Entry (09:45–12:00):** band = daily VWAP ± 1σ (250-bar stdev). **Long:** `close > upper band` and `close > open` and `ER(20) > 0.65` and `close > daily VWAP`. **Short:** mirror.
- **Stop / Target:** 2.5 × ATR / 6 × ATR.
- **Exit:** bracket, or 15:55 close.
- **Sizing:** low-vol ATR% tier (0.1 / 0.25).
- **Character:** best reward profile (winners run to +2.36 R). Bidirectional and **all-weather**, but the **long side wins and the short side is the loser**. In the shared-slot book it's **88% blocked** (only 40 of 345 signals taken) — it fires when the slot is usually busy. Standalone it's +$171k; in the book, +$25k.

---

## Regime cheat-sheet
| Regime | Which subs earn |
|---|---|
| **Strong uptrend** | S1, S2, S6-long (S3/S4 bleed — the hedge cost) |
| **Strong downtrend / correction** | S3, S4 (the shorts feast); S6-short |
| **Range / chop** | S2, S5, S6 (S1 whipsaws) |
| **High-VIX stress** | S1 likes it; **S3 gets squeezed** (its worst condition) |
| **Low-vol overnight contango** | S5 (its entire niche) |

**The book as a whole is regime-balanced** — the short sleeves hedge the long sleeves, so it earns across up, down and range regimes. "Losers" are mostly the right strategy firing in the wrong regime, which is the price of all-weather coverage.

---
*Aston Monnach · strategy reference · derived from the audited 9-year validation.*
