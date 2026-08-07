import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

query = """
SELECT
    symbol,
    change_pct
FROM stocks_daily
WHERE trade_date = (
    SELECT MAX(trade_date)
    FROM stocks_daily
)
"""

df = pd.read_sql(query, conn)

conn.close()

advancing = len(df[df["change_pct"] > 0])

declining = len(df[df["change_pct"] < 0])

unchanged = len(df[df["change_pct"] == 0])

if declining > 0:
    ad_ratio = round(
        advancing / declining,
        2
    )
else:
    ad_ratio = "Infinity"

print("\n" + "=" * 50)
print("MARKET BREADTH")
print("=" * 50)

print(f"\nAdvancing Stocks : {advancing}")
print(f"Declining Stocks : {declining}")
print(f"Unchanged Stocks : {unchanged}")

print(f"\nAdvance/Decline Ratio : {ad_ratio}")

if isinstance(ad_ratio, float):

    if ad_ratio > 1.5:
        print("\nBreadth Status : STRONGLY POSITIVE")

    elif ad_ratio > 1:
        print("\nBreadth Status : POSITIVE")

    elif ad_ratio < 0.7:
        print("\nBreadth Status : STRONGLY NEGATIVE")

    else:
        print("\nBreadth Status : NEGATIVE")

bullish = len(df[df["change_pct"] > 2])

bearish = len(df[df["change_pct"] < -2])

neutral = len(
    df[
        (df["change_pct"] >= -2)
        &
        (df["change_pct"] <= 2)
    ]
)

print(f"Neutral (-2% to +2%) : {neutral}")

print(f"Bullish (>2%)   : {bullish}")
print(f"Bearish (<-2%)  : {bearish}")

breadth_pct = round((advancing / len(df)) * 100, 2)

print(f"Participation   : {breadth_pct}%")