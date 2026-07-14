import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def build_market_regimes():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT
        trade_date,
        close
    FROM indices_daily
    WHERE index_name='NIFTY50'
    ORDER BY trade_date
    """

    df = pd.read_sql(query, conn)

    if len(df) == 0:

        print("No NIFTY data found.")
        conn.close()
        return

    df["sma20"] = (
        df["close"]
        .rolling(20)
        .mean()
    )

    df["sma50"] = (
        df["close"]
        .rolling(50)
        .mean()
    )

    def get_regime(row):

        if pd.isna(row["sma20"]) or pd.isna(row["sma50"]):
            return None

        if (
            row["close"] > row["sma20"]
            and
            row["sma20"] > row["sma50"]
        ):
            return "BULLISH"

        elif (
            row["close"] < row["sma20"]
            and
            row["sma20"] < row["sma50"]
        ):
            return "BEARISH"

        else:
            return "SIDEWAYS"

    df["regime"] = df.apply(
        get_regime,
        axis=1
    )

    df = df.dropna(
        subset=["regime"]
    )

    conn.execute("""
    CREATE TABLE IF NOT EXISTS market_regime (

        trade_date DATE PRIMARY KEY,

        nifty_close REAL,

        sma20 REAL,

        sma50 REAL,

        regime TEXT
    )
    """)

    records = []

    for _, row in df.iterrows():

        records.append(
            (
                row["trade_date"],
                row["close"],
                row["sma20"],
                row["sma50"],
                row["regime"]
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO market_regime (

            trade_date,
            nifty_close,
            sma20,
            sma50,
            regime

        ) VALUES (?, ?, ?, ?, ?)
        """,
        records
    )

    conn.commit()

    print("\n" + "=" * 70)
    print("MARKET REGIME DETECTOR")
    print("=" * 70)

    print(
        f"\nRows Saved : {len(records)}"
    )

    print("\nRegime Counts:\n")

    print(
        df["regime"]
        .value_counts()
    )

    print("\nLatest Regime:")

    latest = (
        df.sort_values("trade_date")
        .iloc[-1]
    )

    print(
        latest["trade_date"],
        latest["regime"]
    )

    print("\n" + "=" * 70)

    conn.close()


if __name__ == "__main__":

    build_market_regimes()