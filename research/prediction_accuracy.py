import pandas as pd

from database.db import get_connection


def prediction_accuracy():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT *
        FROM prediction_outcomes
        """,
        conn
    )

    conn.close()

    if df.empty:

        print("No predictions evaluated.")

        return

    accuracy = (
        df["prediction_correct"]
        .mean()
        * 100
    )

    print()

    print("=" * 60)

    print("MODEL ACCURACY")

    print("=" * 60)

    print(f"Accuracy : {accuracy:.2f}%")