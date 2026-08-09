import sqlite3
import pandas as pd
from pathlib import Path

from analytics.sector_mapping import SECTORS

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_sector_strength():

    conn = sqlite3.connect(str(DB_PATH))

    results = []

    for sector, stocks in SECTORS.items():

        stock_list = ",".join(
            [f"'{s}'" for s in stocks]
        )

        query = f"""
        SELECT
            AVG(change_pct) as avg_change
        FROM stocks_daily
        WHERE symbol IN ({stock_list})
        AND trade_date = (
            SELECT MAX(trade_date)
            FROM stocks_daily
        )
        """

        df = pd.read_sql(query, conn)

        avg_change = round(
            float(df["avg_change"].iloc[0]),
            2
        )

        results.append(
            [sector, avg_change]
        )

    conn.close()

    sector_df = pd.DataFrame(
        results,
        columns=[
            "Sector",
            "Average Change %"
        ]
    )

    sector_df = sector_df.sort_values(
        by="Average Change %",
        ascending=False
    )

    return sector_df

def strongest_sector(df):

    sector = (

        df.groupby("sector")["intelligence_score"]

        .mean()

        .sort_values(ascending=False)

    )

    return sector

# -----------------------------------
# STANDALONE EXECUTION
# -----------------------------------

if __name__ == "__main__":

    sector_df = get_sector_strength()

    print("\nSECTOR STRENGTH\n")

    print(
        sector_df.to_string(
            index=False
        )
    )
