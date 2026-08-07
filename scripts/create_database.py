import sqlite3
from pathlib import Path

# --------------------------------------------------
# DATABASE PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

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

print("Database schema loaded successfully.")

cursor = conn.cursor()

try:
    conn.executescript(sql_script)
except Exception as e:

    print("\nERROR while creating database:")
    print(e)

    raise

# --------------------------------------------------
# VERIFY TABLES
# --------------------------------------------------

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table';
""")

tables = cursor.fetchall()

print("\nTables Created:")

for table in tables:

    print(table)

conn.commit()
conn.close()

print("\nDatabase created successfully")