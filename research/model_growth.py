import sqlite3
import pandas as pd


def model_growth():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT

            trade_date,

            AVG(intelligence_score) average_score

        FROM prediction_history

        GROUP BY trade_date

        ORDER BY trade_date

    """, conn)

    conn.close()

    if df.empty:

        print("No learning history.")

        return

    print("\nMODEL GROWTH")

    print("-" * 40)

    print(df.tail(20))