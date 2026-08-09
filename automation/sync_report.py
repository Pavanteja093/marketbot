import sqlite3
import pandas as pd


def sync_report():

    conn = sqlite3.connect("market_intelligence.db")

    tables = [

        "stocks_daily",

        "indices_daily",

        "options_summary"

    ]

    print("\nSYNC REPORT")
    print("="*50)

    for table in tables:

        try:

            df = pd.read_sql(

                f"""

                SELECT

                    MIN(trade_date) first_day,

                    MAX(trade_date) last_day,

                    COUNT(*) records

                FROM {table}

                """,

                conn

            )

            print(f"\n{table}")

            print(df)

        except Exception:

            print(f"{table} not available.")

    conn.close()