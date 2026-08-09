import sqlite3
import pandas as pd

from analytics.position_sizer import position_size


def portfolio_manager():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT

            symbol,

            intelligence_score,

            grade

        FROM prediction_history

        WHERE trade_date = (

            SELECT MAX(trade_date)

            FROM prediction_history

        )

    """, conn)

    conn.close()

    if df.empty:

        print("No portfolio.")

        return

    portfolio = position_size(df)

    print("\nPORTFOLIO ALLOCATION")

    print("-" * 60)

    print(portfolio.sort_values(

        "allocation_pct",

        ascending=False

    ))