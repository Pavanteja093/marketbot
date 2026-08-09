import sqlite3
import pandas as pd


def memory_statistics():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT
            trade_date,
            intelligence_score

        FROM prediction_history

    """, conn)

    conn.close()

    if df.empty:

        print("No memory yet.")

        return

    print("\nMEMORY STATISTICS")
    print("-"*40)

    print(f"Predictions : {len(df)}")

    print(f"Average Intelligence : {df['intelligence_score'].mean():.2f}")

    print(f"Highest : {df['intelligence_score'].max():.2f}")

    print(f"Lowest : {df['intelligence_score'].min():.2f}")