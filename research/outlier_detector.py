import pandas as pd

from database.db import get_connection


def outlier_detector():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            index_name,
            intelligence_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    mean = df["intelligence_score"].mean()

    std = df["intelligence_score"].std()

    upper = mean + 2 * std

    lower = mean - 2 * std

    outliers = df[
        (df["intelligence_score"] > upper)
        |
        (df["intelligence_score"] < lower)
    ]

    print("\nOutliers")

    print(outliers)


if __name__ == "__main__":
    outlier_detector()