# Aston Monnach · Strategy Validator

The engine that separates a **real edge** from a **backtest mirage** — the checks most traders' own tests quietly skip, which is why *"it passes everything I throw at it"* usually means the tests are too soft. This is the toolkit used to validate the STS book (port notes in [`STS_PORT_README.md`](STS_PORT_README.md); results in [`STS_RESULTS.md`](STS_RESULTS.md)).

## The tool

**`strategy_validator.py`** — feed it a strategy's trade list and it runs the full statistical gauntlet, printing a **PASS / CONCERNS / FAIL** verdict with reasons.

```python
from strategy_validator import validate
trades = [{"R": 1.5, "entry_ts": "2025-03-04T14:30:00"}, ...]  # R = profit in units of initial risk
validate(trades, "STS · S1")
```

Or run the built-in demo:  `python strategy_validator.py`

**What it checks:**
1. Sample size (≥100 trades or it's noise)
2. Edge — win% / profit factor / expectancy
3. **Tail-dependence** — does the edge survive removing the top 3–5 winners?
4. **Out-of-sample** — build on old data, test on held-out recent data
5. **Significance** — per-trade *and* day-level t-stat + 95% CI (must exclude zero)
6. Max drawdown (chronological)
7. Longest losing run
8. Risk of ruin (Monte Carlo)

## Applied to the STS book

| file | what it is |
|---|---|
| `sts_port.py` / `sts_solo.py` | the Pine→Python port that generated the trade lists |
| `STS_strategies.pine` | the six subs as independent Pine scripts |
| `trades_NQ_STS_9yr.csv`, `trades_2026_forward.csv` | the trade lists fed to the validator |
| `STS_RESULTS.md` | the per-sub scoreboard (9yr + 2026 forward) |
| `sts_solo_curves.png`, `sts_overfit.png` | equity curves + overfitting check |

---
*Run every strategy through this before a single pound touches live. If it passes everything, re-check out-of-sample and vs buy-and-hold — that's where 90% quietly die.*
