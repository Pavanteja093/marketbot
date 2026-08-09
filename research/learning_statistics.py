import sqlite3
import pandas as pd


def learning_statistics():

    conn = sqlite3.connect("market_intelligence.db")

    try:

        df = pd.read_sql(
            """
            SELECT prediction_correct
            FROM prediction_history
            WHERE prediction_correct IS NOT NULL
            """,
            conn
        )

    finally:

        conn.close()

    if df.empty:

        print("\nNo validated predictions yet.")

        return

    accuracy = df["prediction_correct"].mean() * 100

    print("\n" + "=" * 50)
    print("LEARNING STATISTICS")
    print("=" * 50)
    print(f"Validated Predictions : {len(df)}")
    print(f"Accuracy              : {accuracy:.2f}%")