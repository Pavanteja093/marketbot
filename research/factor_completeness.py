import sqlite3
import pandas as pd


def factor_completeness():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql(
        "SELECT * FROM factor_history",
        conn
    )

    conn.close()

    print("\n" + "=" * 60)
    print("FACTOR COMPLETENESS")
    print("=" * 60)

    report = pd.DataFrame({

        "Missing %": df.isna().mean() * 100,

        "Available %": df.notna().mean() * 100

    })

    print(report.round(2))