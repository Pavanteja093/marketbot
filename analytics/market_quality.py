import pandas as pd

from database.db import get_connection


def market_quality():

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

    quality = round(df["intelligence_score"].mean(),2)

    print()

    print("="*60)

    print("MARKET QUALITY")

    print("="*60)

    print("Quality Score :",quality)

    return quality


if __name__=="__main__":

    market_quality()