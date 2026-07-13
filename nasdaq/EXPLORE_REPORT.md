MARKET EXPLORE — cross-asset descriptive looking (no entries). Honest: effect sizes + sub-period splits shown.

==================== FUTURES ====================
[NQ] busiest ET half-hours ~ [17.5, 9.5, 10.0] | day-HIGH peaks hr [9, 15, 10] (70% in top-3h) | day-LOW peaks hr [9, 10, 15] (69%)
[NQ] vol clustering: corr(prior10d range, next-day range)=+0.51 | quietest-decile next-day range 0.98% vs avg 1.68% (quiet PERSISTS)
[NQ] autocorr 5m:-0.005 15m:+0.002 1h:-0.006 4h:-0.001 1D:-0.106
[ES] busiest ET half-hours ~ [9.5, 17.5, 10.0] | day-HIGH peaks hr [15, 9, 10] (68% in top-3h) | day-LOW peaks hr [9, 15, 10] (68%)
[ES] vol clustering: corr(prior10d range, next-day range)=+0.59 | quietest-decile next-day range 0.67% vs avg 1.27% (quiet PERSISTS)
[ES] autocorr 5m:-0.014 15m:-0.003 1h:-0.012 4h:-0.021 1D:-0.080

==================== CRYPTO ====================
[BTC] busiest UTC half-hours ~ [14.5, 15.0, 13.5] | day-HIGH peaks hr [0, 15, 23] (26% in top-3h) | day-LOW peaks hr [0, 23, 1] (27%)
[BTC] vol clustering: corr(prior10d range, next-day range)=+0.20 | quietest-decile next-day range 2.82% vs avg 3.75% (quiet PERSISTS)
[BTC] autocorr 5m:-0.023 15m:-0.008 1h:-0.020 4h:-0.008 1D:-0.035
[SOL] busiest UTC half-hours ~ [14.5, 15.0, 16.0] | day-HIGH peaks hr [0, 23, 1] (28% in top-3h) | day-LOW peaks hr [0, 23, 1] (29%)
[SOL] vol clustering: corr(prior10d range, next-day range)=+0.25 | quietest-decile next-day range 5.32% vs avg 7.23% (quiet PERSISTS)
[SOL] autocorr 5m:-0.047 15m:-0.018 1h:-0.005 4h:-0.005 1D:-0.051

==================== CROSS-ASSET ====================
[daily-return correlation matrix, UTC day, full overlap]
       NQ    ES   BTC   SOL   ETH
NQ   1.00  0.93  0.35  0.33  0.47
ES   0.93  1.00  0.34  0.33  0.47
BTC  0.35  0.34  1.00  0.77  0.72
SOL  0.33  0.33  0.77  1.00  0.66
ETH  0.47  0.47  0.72  0.66  1.00
[CRYPTO->NQ OPEN] n=0 days | corr(BTC overnight move, NQ open gap)=+nan | corr(BTC overnight, NQ first-hour ret)=+nan | 2024+ gap-corr +nan
[crypto->NQ] ERR Axis limits cannot be NaN or Inf
Traceback (most recent call last):
  File "C:\Users\thoma\Desktop\market-explore\market_explore.py", line 201, in <module>
    ax.set_xlim(dd.btc_on.quantile(.01)*100,dd.btc_on.quantile(.99)*100)
  File "C:\Users\thoma\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\site-packages\matplotlib\axes\_base.py", line 3828, in set_xlim
    ret

==================== CRYPTO OI / FUNDING / CROWD ====================
[BTC] OI-build->fwd6h-range corr +nan (top-decile OI build 2.29% vs bottom 2.11% vs avg 1.77%) | funding hi->fwd24h -0.03% vs lo +0.35% | crowd(acct_ls)->fwd24h corr -0.06 (2026 -0.06)
[SOL] OI-build->fwd6h-range corr +nan (top-decile OI build 4.51% vs bottom 4.37% vs avg 3.48%) | funding hi->fwd24h +0.04% vs lo +0.26% | crowd(acct_ls)->fwd24h corr -0.09 (2026 -0.07)

========== FIX/EXTEND PASS (crypto->NQ lead, 2026-included; OI/funding/crowd) ==========
[NQ] merged 3,090,125 1m bars 2017-05-21 -> 2026-06-12
[CRYPTO->NQ] n=1072 days (2022+ where BTC exists)
   corr(BTC overnight move, NQ OPEN GAP)   = +0.31   <- do they move together into the open
   corr(BTC overnight move, NQ RTH day ret) = -0.03   <- does overnight crypto PREDICT the cash-session day
   2026-only (n=51): gap +0.68 | rthret +0.13
   big BTC-overnight days (top 20% |move|, n=215): NQ RTH continues 44% of the time (50=coin-flip)
   WEEKEND->MON: corr(BTC weekend move, NQ Mon gap)=+0.42 (n=212)
[NQ HIGH/LOW timing]  full(2017-25): HIGH top hrs [9, 15, 10] (70%) LOW [9, 10, 15] (69%)
                      2026 Apr-Jun:  HIGH top hrs [15, 9, 10] (65%) LOW [9, 10, 11] (79%)  <- holds fresh?
[BTC] OI change -> next-6h range: signed corr +0.02 | |OI change| corr +0.09  (U-shape: extremes move more)
        OI decile range: quietest 2.11% | mid 1.52% | biggest-build 2.29% (avg 1.77%)
        funding hi->fwd24h -0.03% vs lo +0.35% | crowd(acct_ls)->fwd24h corr -0.06 (2026 -0.06)
[SOL] OI change -> next-6h range: signed corr +0.01 | |OI change| corr +0.18  (U-shape: extremes move more)
        OI decile range: quietest 4.37% | mid 2.98% | biggest-build 4.51% (avg 3.48%)
        funding hi->fwd24h +0.04% vs lo +0.26% | crowd(acct_ls)->fwd24h corr -0.09 (2026 -0.07)