import sqlite3
import pandas as pd


def update_memory():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT
            index_name,
            intelligence_score,
            trade_date

        FROM factor_history

        ORDER BY trade_date

    """, conn)

    conn.close()

    if df.empty:

        print("No memory data.")

        return

    latest = (

        df.groupby("index_name")

        .tail(5)

    )

    print("\n" + "=" * 60)

    print("MARKET MEMORY")

    print("=" * 60)

    print(latest)