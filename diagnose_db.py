import sqlite3

try:
    conn = sqlite3.connect("market_intelligence.db")

    cur = conn.cursor()

    print("SQLite Version:", sqlite3.sqlite_version)

    for pragma in [
        "page_size",
        "page_count",
        "schema_version",
        "user_version",
        "application_id"
    ]:
        try:
            value = cur.execute(f"PRAGMA {pragma};").fetchone()
            print(f"{pragma}: {value}")
        except Exception as e:
            print(f"{pragma}: ERROR -> {e}")

except Exception as e:
    print(e)