import sqlite3

from database.db import get_connection


def database_health():

    conn = get_connection()

    cursor = conn.cursor()

    tables = [

        "stocks_daily",

        "indices_daily",

        "factor_history"

    ]

    print("\nDATABASE HEALTH")

    print("-" * 40)

    for table in tables:

        cursor.execute(

            f"SELECT COUNT(*) FROM {table}"

        )

        count = cursor.fetchone()[0]

        print(f"{table:<20}{count:>10}")

    conn.close()


if __name__ == "__main__":

    database_health()