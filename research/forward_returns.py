import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def calculate_forward_returns():

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute("""
    CREATE TABLE IF NOT EXISTS forward_returns (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    symbol TEXT,

    return_1d REAL,
    return_5d REAL,
    return_10d REAL,
    return_20d REAL
    )
    """)
    # -----------------------------
    # Load Stock History
    # -----------------------------

    query = """
    SELECT
        trade_date,
        symbol,
        close
    FROM stocks_daily
    ORDER BY symbol, trade_date
    """

    df = pd.read_sql(query, conn)

    df["trade_date"] = (
        pd.to_datetime(df["trade_date"])
        .dt.strftime("%Y-%m-%d")
    )

    # -----------------------------
    # Future Prices
    # -----------------------------

    df["close_1d"] = (
        df.groupby("symbol")["close"]
        .shift(-1)
    )

    df["close_5d"] = (
        df.groupby("symbol")["close"]
        .shift(-5)
    )

    df["close_10d"] = (
        df.groupby("symbol")["close"]
        .shift(-10)
    )

    df["close_20d"] = (
        df.groupby("symbol")["close"]
        .shift(-20)
    )

    # -----------------------------
    # Returns
    # -----------------------------

    df["return_1d"] = (
        (df["close_1d"] - df["close"])
        / df["close"]
    ) * 100

    df["return_5d"] = (
        (df["close_5d"] - df["close"])
        / df["close"]
    ) * 100

    df["return_10d"] = (
        (df["close_10d"] - df["close"])
        / df["close"]
    ) * 100

    df["return_20d"] = (
        (df["close_20d"] - df["close"])
        / df["close"]
    ) * 100

    # -----------------------------
    # Keep Required Columns
    # -----------------------------

    result = df[
        [
            "trade_date",
            "symbol",
            "return_1d",
            "return_5d",
            "return_10d",
            "return_20d"
        ]
    ].copy()

    # -----------------------------
    # Remove Existing Data
    # -----------------------------

    conn.execute(
        "DELETE FROM forward_returns"
    )

    # -----------------------------
    # Save To Database
    # -----------------------------

    result.to_sql(
        "forward_returns",
        conn,
        if_exists="append",
        index=False
    )

    conn.commit()
    conn.close()

    print(
        f"\nSaved {len(result)} "
        f"forward return records"
    )


if __name__ == "__main__":

    calculate_forward_returns()