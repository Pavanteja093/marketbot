import sqlite3

import pandas as pd


def factor_reliability():

    conn = sqlite3.connect("market_intelligence.db")

    try:

        df = pd.read_sql(

            """

            SELECT *

            FROM factor_history

            """,

            conn

        )

    finally:

        conn.close()

    numeric = df.select_dtypes(include="number")

    stability = (

        numeric.std()

        /

        numeric.mean().abs()

    ).sort_values()

    print("\n")

    print("=" * 60)

    print("FACTOR RELIABILITY")

    print("=" * 60)

    print(stability.round(3))