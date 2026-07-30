import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def inspect_forward_returns():

    conn = sqlite3.connect(DB_PATH)

    factors = pd.read_sql("""
        SELECT trade_date, symbol
        FROM factor_history
        ORDER BY trade_date, symbol
        LIMIT 10
    """, conn)

    returns = pd.read_sql("""
        SELECT trade_date, symbol
        FROM forward_returns
        ORDER BY trade_date, symbol
        LIMIT 10
    """, conn)

    print("\n========== FACTOR HISTORY ==========")
    print(factors.to_string(index=False))

    print("\n========== FORWARD RETURNS ==========")
    print(returns.to_string(index=False))

    print("\n========== DATE RANGES ==========")

    print("\nFactor History")
    print(pd.read_sql("""
        SELECT
            MIN(trade_date) AS first_date,
            MAX(trade_date) AS last_date,
            COUNT(*) AS rows
        FROM factor_history
    """, conn))

    print("\nForward Returns")
    print(pd.read_sql("""
        SELECT
            MIN(trade_date) AS first_date,
            MAX(trade_date) AS last_date,
            COUNT(*) AS rows
        FROM forward_returns
    """, conn))

    conn.close()


if __name__ == "__main__":
    inspect_forward_returns()