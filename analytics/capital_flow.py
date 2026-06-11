import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

# ----------------------------------
# STRONGEST SECTORS
# ----------------------------------

sector_query = """
SELECT
    symbol,
    change_pct
FROM stocks_daily
WHERE trade_date = (
    SELECT MAX(trade_date)
    FROM stocks_daily
)
"""

stocks_df = pd.read_sql(sector_query, conn)

conn.close()

# ----------------------------------
# SECTOR MAPPING
# ----------------------------------

SECTORS = {
    "BANKING": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "KOTAKBANK.NS",
        "INDUSINDBK.NS",
        "AXISBANK.NS"
    ],

    "IT": [
        "TCS.NS",
        "INFY.NS",
        "HCLTECH.NS",
        "TECHM.NS"
    ],

    "PHARMA": [
        "SUNPHARMA.NS",
        "DRREDDY.NS",
        "CIPLA.NS"
    ],

    "AUTO": [
        "MARUTI.NS",
        "M&M.NS",
        "BAJAJ-AUTO.NS",
        "HEROMOTOCO.NS"
    ],

    "METALS": [
        "TATASTEEL.NS",
        "JSWSTEEL.NS",
        "HINDALCO.NS",
        "COALINDIA.NS"
    ],

    "FMCG": [
        "ITC.NS",
        "HINDUNILVR.NS",
        "NESTLEIND.NS",
        "BRITANNIA.NS",
        "TATACONSUM.NS"
    ],

    "ENERGY": [
        "RELIANCE.NS",
        "ONGC.NS",
        "BPCL.NS"
    ]
}

# ----------------------------------
# CALCULATE SECTOR STRENGTH
# ----------------------------------

sector_scores = []

for sector, members in SECTORS.items():

    sector_df = stocks_df[
        stocks_df["symbol"].isin(members)
    ]

    if len(sector_df) > 0:

        avg_change = round(
            sector_df["change_pct"].mean(),
            2
        )

        sector_scores.append(
            [sector, avg_change]
        )

sector_scores = pd.DataFrame(
    sector_scores,
    columns=["Sector", "Strength"]
)

sector_scores = sector_scores.sort_values(
    by="Strength",
    ascending=False
)

# ----------------------------------
# TOP STOCKS
# ----------------------------------

leaders = stocks_df.sort_values(
    by="change_pct",
    ascending=False
).head(5)

# ----------------------------------
# REPORT
# ----------------------------------

print("\n" + "=" * 60)
print("CAPITAL FLOW REPORT")
print("=" * 60)

print("\nSTRONGEST SECTORS\n")
print(sector_scores.head(3))

print("\nWEAKEST SECTORS\n")
print(sector_scores.tail(3))

print("\nLEADING STOCKS\n")
print(
    leaders[
        ["symbol", "change_pct"]
    ]
)

print("\nINTERPRETATION\n")

best_sector = sector_scores.iloc[0]["Sector"]

print(
    f"Capital appears to be rotating into "
    f"{best_sector}."
)