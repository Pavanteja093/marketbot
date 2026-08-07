import pandas as pd

from database.db import get_connection


def learning_statistics():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            prediction_correct
        FROM factor_history
        """,
        conn
    )

    conn.close()

    if df.empty:
        return

    accuracy = (
        df["prediction_correct"]
        .mean()
        * 100
    )

    print()
    print("=" * 60)
    print("LEARNING STATISTICS")
    print("=" * 60)
    print(f"Prediction Accuracy : {accuracy:.2f}%")

    return accuracy


if __name__ == "__main__":
    learning_statistics()