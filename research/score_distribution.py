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
        print("No data.")
        return

    print("\n" + "=" * 60)
    print("INTELLIGENCE SCORE DISTRIBUTION")
    print("=" * 60)

    print(df["intelligence_score"].describe())

    print("\nDistribution")

    bins = [0,20,40,60,80,100]

    distribution = pd.cut(
        df["intelligence_score"],
        bins=bins
    ).value_counts().sort_index()

    print(distribution)


if __name__ == "__main__":
    score_distribution()