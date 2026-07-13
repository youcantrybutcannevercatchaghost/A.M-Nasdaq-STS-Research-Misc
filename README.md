# A.M — Nasdaq & STS Research

Two bodies of NQ (Nasdaq-100 futures) work, held to one standard: **verification-first** — assume every result is wrong until it survives an adversarial check, a fresh out-of-sample year, and realistic costs.

- **[`sts-validation/`](sts-validation/)** — independent, third-party validation of a 6-strategy systematic NQ book ("STS"), **including a full Pine → Python port of all six strategies** so they could be tested on 9 years of data.
- **[`nasdaq/`](nasdaq/)** — original research into how the NQ session actually behaves: where the daily turn forms, what a real top/bottom is made of, and honest backtests of common liquidity setups.

---

## `sts-validation/` — porting & validating the book

The headline: **all six strategies were rebuilt in Python from their Pine source — which was said couldn't be done** — and that unlocked a **9-year backtest** the free platform can't display. The port was then put through a **4-dimension adversarial code audit** (look-ahead, Pine fidelity, accounting, sizing) that **found and fixed 4 real divergences**, and each strategy run through an 8-check gauntlet (Monte Carlo, out-of-sample, concentration, significance).

**Result: 5 of 6 passed. S4 (Short-ORB) failed** — not significant, negative on the fresh year — and it's *documented, not buried.*

| file | what it is |
|---|---|
| `strategy_validator.py` | the validation gauntlet — feed it a trade list, it runs the full battery |
| `STS_strategies.pine` | the six strategies as independent Pine scripts |
| `bb_double_purge.py`, `rd_backtest.py`, `dualst_backtest.py`, `crypto_strats.py`, `multiscale.py`, `strategy_ema200.py` | the Python ports / adaptations |
| `trades_NQ_STS_9yr.csv`, `trades_2026_forward.csv`, `*_trades.json` | the 9-year + forward results |
| `STS_PORT_README.md`, `STRATEGY_REFERENCE.md` | port notes + methodology |
| `sts_solo_curves.png`, `sts_overfit.png` | equity curves + the overfitting check |

## `nasdaq/` — NQ open & market-structure research

9 years of 1-minute NQ + ES with a fresh **2026** gate. **What's real:** the day's high or low prints in the first hour ~80% of the time; a real extreme is a volume-climax rejection with absorption; stacked levels reject ~69% (single levels are a coin flip). **What's not:** FVG / sweep / BOS don't *detect* tops, and the mechanical ICT-style entries lose — documented honestly. Full write-up in [`nasdaq/README.md`](nasdaq/README.md).

---

## Notes
- **Raw data not included** (large / licensed). The validator runs on the **included trade lists**, so the validation is fully reproducible; the backtest scripts reference placeholder `DATA/` paths — point them at your own bars to regenerate.
- Shared for mutual strategy validation and collaboration.

---
*By Aston Monnach.*
