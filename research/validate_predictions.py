import pandas as pd

from database.db import get_connection


def validate_predictions():

    conn = get_connection()

    predictions = pd.read_sql(
        """
        SELECT
            id,
            trade_date,
            index_name,
            prediction
        FROM prediction_history
        WHERE prediction_correct = 0
        """,
        conn
    )

    returns = pd.read_sql(
        """
        SELECT
            trade_date,
            index_name,
            return_5d
        FROM forward_returns
        """,
        conn
    )

    if predictions.empty:

        print("No pending predictions.")

        conn.close()
        return

    merged = predictions.merge(
        returns,
        on=["trade_date", "index_name"],
        how="left"
    )

    for _, row in merged.iterrows():

        if pd.isna(row["return_5d"]):
            continue

        correct = (
            row["prediction"] == "BUY"
            and row["return_5d"] > 0
        ) or (
            row["prediction"] == "SELL"
            and row["return_5d"] < 0
        )

        conn.execute(
            """
            UPDATE prediction_history
            SET
                actual_return=?,
                prediction_correct=?
            WHERE id=?
            """,
            (
                row["return_5d"],
                int(correct),
                row["id"]
            )
        )

    conn.commit()
    conn.close()

    print("Predictions validated.")