import sqlite3

try:
    conn = sqlite3.connect("market_intelligence.db")

    print("SQLite Version:", sqlite3.sqlite_version)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table';
    """)

    tables = cursor.fetchall()

    print("\nTables:")

    for table in tables:
        print(table)

    print("\nDatabase opened successfully.")

except Exception as e:
    print(type(e).__name__)
    print(e)