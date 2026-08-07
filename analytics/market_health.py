import pandas as pd

from database.db import get_connection


def market_health():

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
        return None

    return {

        "average":
            round(
                df["intelligence_score"].mean(),
                2
            ),

        "highest":
            round(
                df["intelligence_score"].max(),
                2
            ),

        "lowest":
            round(
                df["intelligence_score"].min(),
                2
            )

    }


if __name__ == "__main__":

    print(market_health())