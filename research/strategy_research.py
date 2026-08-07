import pandas as pd

from database.db import get_connection


def strategy_research():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            signal,
            confidence,
            intelligence_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    if df.empty:
        return

    print("\n" + "=" * 60)
    print("STRATEGY RESEARCH")
    print("=" * 60)

    print(df.groupby("signal").size())

    print()

    print(df.groupby("signal")["confidence"].mean())

    print()

    print(df.groupby("signal")["intelligence_score"].mean())


if __name__ == "__main__":
    strategy_research()