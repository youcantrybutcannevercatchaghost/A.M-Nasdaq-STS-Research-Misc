# Aston Monnach · Strategy Validator

**By Aston Monnach** —


> Aston Monnach.
> © Aston Monnach.

---

The engine that separates a **real edge** from a **backtest mirage** — the checks that most
traders' own tests quietly skip, which is why "it passes everything I throw at it" usually
means the tests are too soft.

## The main tool

**`strategy_validator.py`** — feed it a strategy's trade list and it runs the full
statistical gauntlet, printing a **PASS / CONCERNS / FAIL** verdict with reasons.

```python
from strategy_validator import validate
trades = [{"R": 1.5, "entry_ts": "2025-03-04T14:30:00"}, ...]  # R = profit in units of initial risk
validate(trades, "My Strategy · BTC 15m")
```

Or just run it for the built-in demo:  `python strategy_validator.py`

**What it checks:**
1. Sample size (≥100 trades or it's noise)
2. Edge — win% / profit factor / expectancy
3. **Tail-dependence** — does the edge survive removing the top 3–5 winners?
4. **Out-of-sample** — build on old data, test on held-out recent data
5. **Significance** — per-trade *and* day-level t-stat + 95% CI (must exclude zero)
6. Max drawdown (chronological)
7. Longest losing run
8. Risk of ruin (Monte Carlo)

## The execution-realism engines (per-strategy)

The statistical tool answers *"is the claimed edge real?"* The half that answers
*"will it survive real fills?"* needs the strategy's own code + data — reference implementations:

| File | What it does |
|------|--------------|
| `dualst_backtest.py` | **The reality-check pattern** — optimistic vs realistic (next-bar-open entry, known-before-bar stops, real fees + slippage). This is what caught the "+840% → −37%" look-ahead phantom. |
| `strategy_ema200.py` | Trend-follow test **vs buy-and-hold** (the check that kills long-only strats on trending assets). |
| `bb_double_purge.py` | Bollinger-band double-purge detector + realistic sim. |
| `rd_backtest.py` | Range-Deviation detector (swing ranges, SFP, iBOS, OF zone). |
| `multiscale.py` | Multi-scale range pooling. |

## Data included
`btc_15m` · `sol_15m` (2yr Binance perp) · `nq_4h` · `btc_4h` (2018→) · `rd_trades.json` · `bb_trades.json`

---
*Run every strategy through this before a single pound touches live. If it passes everything,
check #1 (execution realism) and #4 (vs buy-and-hold) again — that's where 90% quietly die.*
