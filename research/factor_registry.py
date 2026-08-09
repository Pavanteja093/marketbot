import sqlite3
import pandas as pd


def factor_registry():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql(
        "SELECT * FROM factor_history",
        conn
    )

    conn.close()

    print("\nFACTOR REGISTRY")
    print("-" * 50)

    for column in df.columns:

        if column in ["trade_date", "index_name"]:
            continue

        print(f"{column:<30} Available")