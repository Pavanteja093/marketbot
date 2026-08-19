import pandas as pd

from database.db import get_connection


def factor_performance():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            intelligence_score,
            return_5d
        FROM forward_returns f
        JOIN factor_history h
            ON f.index_name=h.index_name
           AND f.trade_date=h.trade_date
        """,
        conn
    )

    conn.close()

    if df.empty:
        return

    print()
    print("=" * 60)
    print("FACTOR PERFORMANCE")
    print("=" * 60)

    print(df.describe())


if __name__ == "__main__":
    factor_performance()

