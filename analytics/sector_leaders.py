import pandas as pd

from database.db import get_connection


def sector_leaders():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT *
        FROM factor_history
        ORDER BY intelligence_score DESC
        """,
        conn
    )

    conn.close()

    leaders = (

        df

        .groupby("sector")

        .first()

        .reset_index()

    )

    return leaders


if __name__ == "__main__":
    print(sector_leaders())