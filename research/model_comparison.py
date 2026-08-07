import pandas as pd

from database.db import get_connection


def compare_models():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            prediction,
            prediction_correct
        FROM factor_history
        """,
        conn
    )

    conn.close()

    if df.empty:
        return

    print()
    print("=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)

    print(

        df.groupby("prediction")["prediction_correct"]

        .mean()

        .round(3)

    )


if __name__ == "__main__":
    compare_models()