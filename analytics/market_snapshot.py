import pandas as pd

from database.db import get_connection


def build_market_snapshot():

    conn = get_connection()

    df = pd.read_sql("""

        SELECT *

        FROM factor_history

        ORDER BY intelligence_score DESC

    """, conn)

    conn.close()

    if df.empty:

        print("No data available.")

        return

    print("\n==============================")

    print("Today's Strongest Stocks")

    print("==============================")

    print(

        df[
            [

                "index_name",

                "intelligence_score"

            ]

        ].head(10)

    )

    print()

    print("Average Intelligence :",

        round(df["intelligence_score"].mean(), 2))

    print("Highest Score :",

        round(df["intelligence_score"].max(), 2))

    print("Lowest Score :",

        round(df["intelligence_score"].min(), 2))


if __name__ == "__main__":

    build_market_snapshot()