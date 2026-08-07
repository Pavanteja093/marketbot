import pandas as pd

from database.db import get_connection


def feature_drift():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            intelligence_score
        FROM factor_history
        ORDER BY trade_date
        """,
        conn
    )

    conn.close()

    if df.empty:
        return

    drift = (
        df.groupby("trade_date")
        ["intelligence_score"]
        .mean()
    )

    print("\nAverage Score Drift")

    print(drift)
    

if __name__ == "__main__":
    feature_drift()