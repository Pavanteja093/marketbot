import sqlite3
import pandas as pd
from pathlib import Path

from analytics.sector_mapping import SECTORS
from analytics.trend_intelligence import get_trend_intelligence

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_stock_scores_v2(trade_date=None):

    conn = sqlite3.connect(str(DB_PATH))

    if trade_date is None:

        query = """
        SELECT
            symbol,
            close,
            volume,
            change_pct
        FROM stocks_daily
        WHERE trade_date = (
            SELECT MAX(trade_date)
            FROM stocks_daily
        )
        """

    else:

        query = f"""
        SELECT
            symbol,
            close,
            volume,
            change_pct
        FROM stocks_daily
        WHERE trade_date = '{trade_date}'
        """

    df = pd.read_sql(query, conn)

    conn.close()

    # ----------------------------------
    # Sector Mapping
    # ----------------------------------

    sector_lookup = {}

    for sector, stocks in SECTORS.items():

        for stock in stocks:

            sector_lookup[stock] = sector

    df["sector"] = df["symbol"].map(
        sector_lookup
    )

    # ----------------------------------
    # Sector Strength
    # ----------------------------------

    sector_strength = (
        df.groupby("sector")["change_pct"]
        .mean()
        .to_dict()
    )

    df["sector_strength"] = (
        df["sector"]
        .map(sector_strength)
    )

    # ----------------------------------
    # Trend Intelligence
    # ----------------------------------

    trend_df = get_trend_intelligence(
        trade_date
    )

    df = df.merge(
        trend_df[
            [
                "symbol",
                "position_pct"
            ]
        ],
        on="symbol",
        how="left"
    )

    # ----------------------------------
    # Scores
    # ----------------------------------

    df["price_score"] = (
        df["change_pct"].rank(pct=True) * 30
    )

    df["volume_score"] = (
        df["volume"].rank(pct=True) * 20
    )

    df["sector_score"] = (
        df["sector_strength"]
        .rank(pct=True) * 20
    )

    df["trend_score"] = (
        df["position_pct"]
        .rank(pct=True) * 30
    )

    # ----------------------------------
    # Intelligence Score
    # ----------------------------------

    df["intelligence_score"] = (
        df["price_score"] +
        df["volume_score"] +
        df["sector_score"] +
        df["trend_score"]
    )

    # ----------------------------------
    # Grade
    # ----------------------------------

    def get_grade(score):

        if score >= 85:
            return "A"

        elif score >= 70:
            return "B"

        else:
            return "C"

    df["grade"] = (
        df["intelligence_score"]
        .apply(get_grade)
    )

    # ----------------------------------
    # Sort
    # ----------------------------------

    df = df.sort_values(
        by="intelligence_score",
        ascending=False
    )

    df = df.reset_index(
        drop=True
    )
    
    return df


# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    df = get_stock_scores_v2()

    print("\n" + "=" * 80)
    print("STOCK SCORING V2")
    print("=" * 80)

    print(
        df[
            [
                "grade",
                "symbol",
                "sector",
                "change_pct",
                "position_pct",
                "intelligence_score"
            ]
        ]
        .head(15)
        .to_string(index=False)
    )