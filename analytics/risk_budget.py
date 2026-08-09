import sqlite3
import pandas as pd


def risk_budget():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT

            symbol,

            intelligence_score,

            volatility_score

        FROM factor_history

        ORDER BY trade_date DESC

    """, conn)

    conn.close()

    if df.empty:

        print("No factor history.")

        return

    df["risk_budget"] = (

        df["intelligence_score"]

        /

        df["volatility_score"]

    ).round(2)

    print("\nRISK BUDGET")

    print("-" * 50)

    print(

        df[

            [

                "symbol",

                "risk_budget"

            ]

        ].head(20)

    )