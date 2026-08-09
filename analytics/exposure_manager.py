import sqlite3
import pandas as pd


def exposure_manager():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT

            sector,

            COUNT(*) stocks,

            AVG(intelligence_score) avg_score

        FROM prediction_history

        WHERE trade_date=(

            SELECT MAX(trade_date)

            FROM prediction_history

        )

        GROUP BY sector

    """, conn)

    conn.close()

    if df.empty:

        print("No exposure.")

        return

    print("\nSECTOR EXPOSURE")

    print("="*60)

    print(df.sort_values(

        "stocks",

        ascending=False

    ))