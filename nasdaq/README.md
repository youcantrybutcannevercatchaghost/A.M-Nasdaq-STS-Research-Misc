# NQ Open & Market-Structure Research

Verification-first research into **where and how the NQ session turn forms**, how price behaves around liquidity levels, and whether common ICT-style ideas survive a real out-of-sample test. Built on **9 years of 1-minute NQ + ES (2017–2025)**, a fresh **2026** gate, and **BTC/SOL order-flow** for cross-asset checks.

The rule throughout: **assume every "edge" is a phantom until it survives a random-price control, a fresh untouched year, and realistic costs.** Most ideas here got *killed* — and the nulls are the point.

## ✅ What's real (kept)

- **The day's high or low prints in the first hour ~78% of the time** (9yr) — **86% in 2026.** The turn is an opening-hour event. → `read_figures.py`, `top_anatomy.py`
- **Fingerprint of a real extreme:** a volume climax (~2× the day's average minute) + a rejection wick (~1.5× a normal bar) + aggressor **absorption** (buyers soaked up *into* the high). → `top_anatomy.py`, `structure_fingerprint.py`
- **Stacked levels reject ~69%** of the time — vs a single level's ~50% (= random). Stacking is the difference. → `cluster_reject.py`
- **Cross-asset:** crypto's weekend move leads the NQ **Monday open gap** (corr +0.42); OI *magnitude* (not direction) tracks forward volatility. → `market_explore.py`, `fix_modules.py`

## ❌ What's NOT real (killed — the honest half)

- **Single levels are a coin flip** — PDH/PDL / session H&L hold ~50%, dead level with a random-price control.
- **FVG / sweep / BOS don't *detect* tops** — they fire at ~the same rate on ordinary swing highs that go nowhere. Only *volume* discriminates. → `structure_fingerprint.py`
- **Mechanical entries lose.** "Stack front-run & dump": **−1,836 pts over 9 years.** "Pullback-to-the-draw": **16% win, −1,831 pts in 2026** — verified by *rendering and eyeballing the actual trades* (wrong direction half the time, target too far, upside-down R:R). The edge is the **discretionary read** — which draw, is the R:R worth it, is the target realistic — not a fixed rule. → `backtest_stack.py`, `backtest_draw.py`, `render_draw_trades.py`
- **The first-hour drive does not predict the day** (continues ~54% ≈ baseline; inverts in 2026).

## Method
Causal / forward-only detection, random-price controls, **2017–25 build + 2026 fresh-year gate**, costs included, and deliberately **no parameter-hunting** (a rule that only works in one wild year isn't kept).

## Files
| file | what it does |
|---|---|
| `market_explore.py`, `fix_modules.py` | cross-asset EDA — activity clock, high/low timing, vol clustering, momentum-vs-reversion, correlations, crypto→NQ lead, OI/funding/crowd |
| `top_anatomy.py` | anatomy of the daily top/bottom — timing, "is-it-in" base rate, bar shape, reversal size |
| `structure_fingerprint.py` | real top vs ordinary swing high — what's actually different |
| `cluster_reject.py` | why price reverses at a stacked cluster vs pushes through to target |
| `backtest_stack.py`, `backtest_draw.py` | honest backtests of the ICT-style setups (both lose; documented why) |
| `contact_sheet.py`, `render_look.py`, `render_mechanics.py`, `render_draw_trades.py` | chart renderers (candles + liquidity map, in a fixed greyscale theme) |
| `*.md` | written findings for each study |
| `look/` | rendered charts |

## Data
Raw 1-minute feeds (NQ/ES 9yr, BTC/SOL flow, 2026) are **not included** — large and from local/licensed sources. Scripts reference local paths; they're here to show **method and results**, not to run turnkey.

---
*Research, not a signal service. The value is in what's true — and what's been ruled out.*
