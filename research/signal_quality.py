import pandas as pd

from database.db import get_connection


def signal_quality():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            intelligence_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    print("\nSignal Distribution")

    print(df["intelligence_score"].describe())


if __name__ == "__main__":
    signal_quality()