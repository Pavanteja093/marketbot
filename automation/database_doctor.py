import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


TABLE_KEYS = {
    "stocks_daily": "symbol",
    "indices_daily": "index_name",
    "factor_history": "index_name",
    "prediction_history": "index_name",
    "signal_history": "index_name",
    "signal_history_v2": "index_name",
    "forward_returns": "index_name",
}


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):

    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def database_doctor():

    print("\n" + "=" * 75)
    print("MARKETBOT DATABASE DOCTOR")
    print("=" * 75)

    conn = sqlite3.connect(str(DB_PATH))

    overall_ok = True

    for table, key_column in TABLE_KEYS.items():

        print(f"\n{table}")

        if not table_exists(conn, table):

            print("  STATUS : MISSING")
            overall_ok = False
            continue

        columns = get_columns(
            conn,
            table
        )

        rows = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(
            f"  Rows   : {rows:,}"
        )

        print(
            f"  Key    : {key_column}"
        )

        if "trade_date" in columns:

            latest = conn.execute(
                f"""
                SELECT MAX(trade_date)
                FROM {table}
                """
            ).fetchone()[0]

            earliest = conn.execute(
                f"""
                SELECT MIN(trade_date)
                FROM {table}
                """
            ).fetchone()[0]

            print(
                f"  Range  : {earliest} -> {latest}"
            )

        if key_column not in columns:

            print(
                f"  STATUS : ERROR - "
                f"{key_column} column missing"
            )

            overall_ok = False
            continue

        if "trade_date" in columns:

            duplicates = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT
                        trade_date,
                        {key_column},
                        COUNT(*) AS c
                    FROM {table}
                    GROUP BY
                        trade_date,
                        {key_column}
                    HAVING c > 1
                )
                """
            ).fetchone()[0]

            print(
                f"  Duplicates : {duplicates}"
            )

            if duplicates > 0:
                overall_ok = False

        print(
            f"  STATUS : {'OK' if rows >= 0 else 'ERROR'}"
        )

    conn.close()

    print("\n" + "-" * 75)

    if overall_ok:

        print("DATABASE DOCTOR: HEALTHY")

    else:

        print(
            "DATABASE DOCTOR: ISSUES DETECTED"
        )

    print("-" * 75)

    return overall_ok


if __name__ == "__main__":
    database_doctor()