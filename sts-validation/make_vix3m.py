# -*- coding: utf-8 -*-
"""
Regenerate vix3m.parquet from CBOE's official VIX3M history.

sts_port.py needs two daily volatility series: vix.parquet and vix3m.parquet.
VIX3M gates S5 only (the overnight sub) via the term-structure test `vix/vix3m < 0.95`
(i.e. front-month VIX below 3-month VIX = contango = calm regime). That gate is true on
~80% of days, and S5 is 445 of the 3,314 trades across 2017-2026.

Source: CBOE publish VIX3M daily history themselves, so this is first-party data, not a mirror.
    https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv

Usage:  python make_vix3m.py
Output: vix3m.parquet  (columns: Date, close) — the shape build() expects.
"""
import io, urllib.request
import pandas as pd

URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv"
OUT = "vix3m.parquet"

def main():
    print(f"fetching {URL}")
    with urllib.request.urlopen(URL, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    c = pd.read_csv(io.StringIO(raw))
    df = pd.DataFrame({
        "Date": pd.to_datetime(c["DATE"], format="%m/%d/%Y"),
        "close": c["CLOSE"].astype(float),
    }).sort_values("Date").reset_index(drop=True)
    df.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(df):,} rows  {df.Date.min().date()} -> {df.Date.max().date()}")

if __name__ == "__main__":
    main()
