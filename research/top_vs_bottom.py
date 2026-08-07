import pandas as pd

from database.db import get_connection


def top_vs_bottom():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            intelligence_score
        FROM factor_history
        ORDER BY intelligence_score DESC
        """,
        conn
    )

    conn.close()

    if len(df) < 10:
        return

    top = df.head(10)

    bottom = df.tail(10)

    print("\nTop Average")

    print(top["intelligence_score"].mean())

    print("\nBottom Average")

    print(bottom["intelligence_score"].mean())


if __name__ == "__main__":
    top_vs_bottom()