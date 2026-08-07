import pandas as pd

from database.db import get_connection


def score_distribution():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT intelligence_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    if df.empty:
        return

    print()
    print("=" * 60)
    print("INTELLIGENCE SCORE DISTRIBUTION")
    print("=" * 60)

    print(

        pd.cut(

            df["intelligence_score"],

            bins=[0,20,40,60,80,100]

        ).value_counts().sort_index()

    )


if __name__ == "__main__":
    score_distribution()