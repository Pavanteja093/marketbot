import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


REQUIRED_TABLES = [
    "stocks_daily",
    "indices_daily",
    "factor_history",
    "prediction_history",
]


def table_exists(conn, table_name):

    return conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table_name,)
    ).fetchone() is not None


def repair_database():

    print("\n" + "=" * 70)
    print("MARKETBOT DATABASE SELF-REPAIR")
    print("=" * 70)

    conn = sqlite3.connect(str(DB_PATH))

    repaired = 0
    healthy = 0
    failed = 0

    for table in REQUIRED_TABLES:

        try:

            if table_exists(conn, table):

                count = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]

                print(
                    f"{table:<25} "
                    f"OK ({count:,} rows)"
                )

                healthy += 1

            else:

                print(
                    f"{table:<25} "
                    f"MISSING"
                )

                failed += 1

        except Exception as exc:

            print(
                f"{table:<25} "
                f"ERROR: {exc}"
            )

            failed += 1

    # -------------------------------------------------------
    # SQLite integrity check
    # -------------------------------------------------------

    try:

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print(
            f"\nSQLite Integrity : {integrity}"
        )

        if integrity != "ok":
            failed += 1

    except Exception as exc:

        print(
            f"Integrity check failed: {exc}"
        )

        failed += 1

    # -------------------------------------------------------
    # WAL checkpoint
    # -------------------------------------------------------

    try:

        conn.execute(
            "PRAGMA wal_checkpoint(PASSIVE)"
        )

    except Exception:
        pass

    conn.close()

    print("\n" + "-" * 70)
    print(
        f"Healthy : {healthy}"
    )
    print(
        f"Repaired: {repaired}"
    )
    print(
        f"Failed  : {failed}"
    )
    print("-" * 70)

    return failed == 0


if __name__ == "__main__":
    repair_database()