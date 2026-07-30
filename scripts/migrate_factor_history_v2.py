import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def column_exists(cursor, table, column):

    cursor.execute(f"PRAGMA table_info({table})")

    columns = [row[1] for row in cursor.fetchall()]

    return column in columns


def main():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    print("=" * 60)
    print("Factor History Migration V2")
    print("=" * 60)

    if not column_exists(cursor, "factor_history", "relative_strength"):

        cursor.execute(
            """
            ALTER TABLE factor_history
            ADD COLUMN relative_strength REAL
            """
        )

        print("✓ Added relative_strength")

    else:

        print("✓ relative_strength already exists")

    if not column_exists(cursor, "factor_history", "rs_grade"):

        cursor.execute(
            """
            ALTER TABLE factor_history
            ADD COLUMN rs_grade TEXT
            """
        )

        print("✓ Added rs_grade")

    else:

        print("✓ rs_grade already exists")

    conn.commit()

    conn.close()

    print("\nMigration completed successfully.")


if __name__ == "__main__":

    main()