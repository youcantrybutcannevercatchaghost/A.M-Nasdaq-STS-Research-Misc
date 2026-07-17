# NQ Open & Market-Structure Research

Verification-first research into **where and how the NQ session turn forms**, how price behaves around liquidity levels, and whether common ICT-style ideas survive a real out-of-sample test. Built on **9 years of 1-minute NQ + ES (2017–2025)** with a fresh **2026** gate.

The rule throughout: **assume every "edge" is a phantom until it survives a random-price control, a fresh untouched year, and realistic costs.** Most ideas here got *killed* — and the nulls are the point.

## ✅ What's real (kept)

- **The day's high or low prints in the first hour ~78% of the time** (9yr) — **86% in 2026.** The turn is an opening-hour event. → `read_figures.py`, `top_anatomy.py`
- **Fingerprint of a real extreme:** a volume climax (~2× the day's average minute) + a rejection wick (~1.5× a normal bar) + aggressor **absorption** (buyers soaked up *into* the high). → `top_anatomy.py`, `structure_fingerprint.py`
## ⚠️ RETRACTION — "stacked levels reject ~69%"

**This repo previously listed *"Stacked levels reject ~69% — stacking is the difference"* under "What's real". That claim is withdrawn.**

- What `cluster_reject.py` actually measured: a **narrow** case — 5m cluster-rallies into a stacked target, **n = 1,072**. Within that definition the 69% reject rate stands, and the script is still here.
- What killed the **generalisation**: re-testing "does stacking change the odds?" across **95,866 level touches (2017–2026)** gives **stacked → 50.8% continue / 49.2% reject**, vs **unstacked → 49.8% continue**. **Indistinguishable. Stacking is not the difference.**
- The 69% was a definition/sample artifact of the narrow test, generalised into a headline it couldn't carry. Single levels are a coin flip — and so are stacked ones.
- *(The 95,866-touch dataset lives outside this repo; the claim is retracted here regardless, because it shouldn't have been stated this broadly on this evidence.)*

The rule at the top of this README says assume every edge is a phantom until it survives. This one didn't, and it was ours.

## ❌ What's NOT real (killed — the honest half)

- **Single levels are a coin flip** — PDH/PDL / session H&L hold ~50%, dead level with a random-price control. **Stacked levels too** (see the retraction above).
- **FVG / sweep / BOS don't *detect* tops** — they fire at ~the same rate on ordinary swing highs that go nowhere. Only *volume* discriminates. → `structure_fingerprint.py`
- **Mechanical entries lose.** "Stack front-run & dump": **−1,836 pts over 9 years.** "Pullback-to-the-draw": **16% win, −1,831 pts in 2026** — verified by *rendering and eyeballing the actual trades* (wrong direction half the time, target too far, upside-down R:R). The edge is the **discretionary read** — which draw, is the R:R worth it, is the target realistic — not a fixed rule. → `backtest_stack.py`, `backtest_draw.py`, `render_draw_trades.py`
- **The first-hour drive does not predict the day** (continues ~54% ≈ baseline; inverts in 2026).

## Method
Causal / forward-only detection, random-price controls, **2017–25 build + 2026 fresh-year gate**, costs included, and deliberately **no parameter-hunting** (a rule that only works in one wild year isn't kept).

## Files
| file | what it does |
|---|---|
| `read_figures.py` | when the turn happens (first hour ~78%) + does the first-hour drive predict the day (no) |
| `top_anatomy.py` | anatomy of the daily top/bottom — timing, "is-it-in" base rate, bar shape, reversal size |
| `structure_fingerprint.py` | real top vs ordinary swing high — what's actually different |
| `cluster_reject.py` | why price reverses at a stacked cluster vs pushes through to target |
| `market_explore.py` | NQ + ES exploratory pass — activity clock, high/low timing, volatility clustering, momentum-vs-reversion |
| `backtest_stack.py`, `backtest_draw.py` | honest backtests of the ICT-style setups (both lose; documented why) |
| `contact_sheet.py`, `render_look.py`, `render_mechanics.py`, `render_draw_trades.py` | chart renderers (candles + liquidity map, fixed greyscale theme) |
| `data/` | labelled datasets — `fvg_dataset.csv` (5,950 FVGs), `flow_touches.csv` (1,071 level touches w/ order flow) |
| `*.md`, `look/` | written findings + rendered charts |

## Data
Raw 1-minute NQ/ES feeds are **not included** (large / licensed) — scripts reference placeholder `DATA/` paths. The labelled `data/*.csv` datasets are self-contained.

---
*Research, not a signal service. The value is in what's true — and what's been ruled out.*
