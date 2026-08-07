import pandas as pd

from database.db import get_connection


def build_sector_rankings():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            sector,
            AVG(intelligence_score) AS avg_score,
            COUNT(*) AS stocks
        FROM factor_history
        WHERE sector IS NOT NULL
        GROUP BY sector
        ORDER BY avg_score DESC
        """,
        conn
    )

    conn.close()

    return df


if __name__ == "__main__":
    print(build_sector_rankings())