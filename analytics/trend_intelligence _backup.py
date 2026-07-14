import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_trend_intelligence():

    conn = sqlite3.connect(str(DB_PATH))

    # -----------------------------
    # Latest Prices
    # -----------------------------

    latest_date_query = """
    SELECT MAX(trade_date) AS trade_date
    FROM stocks_daily
    """

    latest_date = pd.read_sql(
        latest_date_query,
        conn
    ).iloc[0]["trade_date"]

    # -----------------------------
    # Stock History
    # -----------------------------

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            symbol,
            close
        FROM stocks_daily
        ORDER BY trade_date
        """,
        conn
    )

    conn.close()

    results = []

    # -----------------------------
    # Per Stock Analysis
    # -----------------------------

    for symbol in df["symbol"].unique():

        stock = (
            df[df["symbol"] == symbol]
            .sort_values("trade_date")
        )

        current_price = stock.iloc[-1]["close"]

        highest_price = stock["close"].max()

        lowest_price = stock["close"].min()

        distance_high = (
            (
                current_price -
                highest_price
            )
            /
            highest_price
        ) * 100

        distance_low = (
            (
                current_price -
                lowest_price
            )
            /
            lowest_price
        ) * 100

        if highest_price == lowest_price:

            position_pct = 50

        else:

            position_pct = (
                (
                    current_price -
                    lowest_price
                )
                /
                (
                    highest_price -
                    lowest_price
                )
            ) * 100

        results.append([
            symbol,
            round(current_price, 2),
            round(highest_price, 2),
            round(lowest_price, 2),
            round(distance_high, 2),
            round(distance_low, 2),
            round(position_pct, 2)
        ])

    trend_df = pd.DataFrame(
        results,
        columns=[
            "symbol",
            "current_price",
            "highest_price",
            "lowest_price",
            "distance_high_pct",
            "distance_low_pct",
            "position_pct"
        ]
    )

    trend_df = trend_df.sort_values(
        "position_pct",
        ascending=False
    )

    return trend_df


# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    trend_df = get_trend_intelligence()

    print("\n" + "=" * 70)
    print("TREND INTELLIGENCE")
    print("=" * 70)

    print(
        trend_df.head(15).to_string(
            index=False
        )
    )