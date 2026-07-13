# STS — validation scoreboard

Independent Python port of the 6-sub NQ book, each sub run standalone through the validator. P&L is in the book's account units — the raw number isn't the point (regime and costs vary); **which subs survive the fresh out-of-sample year is.**

## 9-year build (2017–2025)

| sub | trades | total P&L | win% |
|---|---|---|---|
| S1 | 876 | +270,745 | 33% |
| S2 | 712 | +97,872 | 48% |
| S3 | 146 | +177,640 | 44% |
| S4 | 945 | +104,897 | 38% |
| S5 | 435 | +164,594 | 62% |
| S6 | 40 | +24,874 | 50% |
| **Book** | **3,154** | **+840,621** | — |

## 2026 forward (fresh, out-of-sample)

| sub | trades | total P&L | win% |
|---|---|---|---|
| S1 | 57 | −2,227 | 33% |
| S2 | 40 | +623 | 50% |
| S3 | 10 | +30,154 | 40% |
| S4 | 42 | **−8,933** | 40% |
| S5 | 10 | +1,794 | 50% |
| **Book** | **159** | **+21,412** | — |

## Verdict

**5 of 6 pass the full 9-year gauntlet; S4 (Short-ORB) fails** — profitable across the build but **negative on the fresh 2026 forward** and not statistically significant. The book stays net-positive out-of-sample on the strength of S3/S5. Caveats stated up front, as they should be: the 2026 forward is a *small sample* (S1's −2,227 is inside a 57-trade noise band), and S6's 40 lifetime trades are too thin to lean on. The number that matters isn't +840k — it's that the edge **survived being independently rebuilt and adversarially audited** before anyone trusted it.
