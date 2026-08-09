import sqlite3
import pandas as pd

from database.db import get_connection


def latest_date(table):

    conn = get_connection()

    query = f"""
        SELECT MAX(trade_date) AS latest
        FROM {table}
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df.iloc[0]["latest"]


def database_health():

    print("\n" + "=" * 60)
    print("DATABASE HEALTH")
    print("=" * 60)

    tables = [
        "stocks_daily",
        "indices_daily",
        "factor_history",
        "forward_returns"
    ]

    for table in tables:

        try:

            print(f"{table:<20} {latest_date(table)}")

        except Exception:

            print(f"{table:<20} Missing")


if __name__ == "__main__":
    database_health()