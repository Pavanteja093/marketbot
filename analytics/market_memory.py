import sqlite3
import pandas as pd


def market_memory():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            index_name,
            intelligence_score
        FROM factor_history
        ORDER BY trade_date
        """,
        conn,
    )

    conn.close()

    if df.empty:
        print("No market memory available.")
        return

    latest = (
        df.groupby("index_name")
        .tail(5)
        .groupby("index_name")["intelligence_score"]
        .mean()
        .sort_values(ascending=False)
    )

    print("\nMARKET MEMORY SNAPSHOT")
    print("-" * 50)
    print(latest.head(15))