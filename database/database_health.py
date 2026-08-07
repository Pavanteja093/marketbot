import pandas as pd

from database.db import get_connection


TABLES = [

    "stocks_daily",

    "factor_history",

    "forward_returns"

]


def database_health():

    conn = get_connection()

    print()
    print("=" * 60)
    print("DATABASE HEALTH")
    print("=" * 60)

    for table in TABLES:

        rows = pd.read_sql(

            f"SELECT COUNT(*) AS rows FROM {table}",

            conn

        )

        print(f"{table:<20} {rows.iloc[0]['rows']:,}")

    conn.close()


if __name__ == "__main__":
    database_health()