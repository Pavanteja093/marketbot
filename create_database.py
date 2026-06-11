import sqlite3
from pathlib import Path

# --------------------------------------------------
# DATABASE PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "market_intelligence.db"

SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

# --------------------------------------------------
# CREATE DATABASE
# --------------------------------------------------

conn = sqlite3.connect(str(DB_PATH))

with open(
    SCHEMA_PATH,
    "r",
    encoding="utf-8"
) as f:

    sql_script = f.read()

print("SQL Loaded:")
print(sql_script)

conn.executescript(sql_script)

conn.commit()

# --------------------------------------------------
# VERIFY TABLES
# --------------------------------------------------

cursor = conn.cursor()

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table';
""")

tables = cursor.fetchall()

print("\nTables Created:")

for table in tables:

    print(table)

conn.close()

print("\nDatabase created successfully")