import sqlite3
import pandas as pd


def database_report():

    conn = sqlite3.connect("market_intelligence.db")

    tables = [
        "stocks_daily",
        "indices_daily",
        "factor_history",
        "prediction_history"
    ]

    print("\n" + "=" * 60)
    print("DATABASE REPORT")
    print("=" * 60)

    for table in tables:

        try:

            rows = pd.read_sql(
                f"SELECT COUNT(*) AS rows FROM {table}",
                conn
            )

            latest = pd.read_sql(
                f"""
                SELECT MAX(trade_date) AS latest
                FROM {table}
                """,
                conn
            )

            print(
                f"{table:22}"
                f" Rows={rows.iloc[0,0]:8}"
                f" Latest={latest.iloc[0,0]}"
            )

        except Exception:

            print(f"{table:22} Missing")

    conn.close()