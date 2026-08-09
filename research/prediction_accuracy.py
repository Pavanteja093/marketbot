import sqlite3
import pandas as pd

from database.db import get_connection


def prediction_accuracy():

    conn = get_connection()

    df = pd.read_sql(

        """

        SELECT

            prediction_correct

        FROM prediction_history

        WHERE prediction IS NOT NULL

        """,

        conn

    )

    conn.close()

    if len(df) == 0:

        print("No predictions yet.")

        return

    accuracy = df.prediction_correct.mean() * 100

    print("\nPrediction Accuracy")

    print("-" * 30)

    print(f"{accuracy:.2f}%")