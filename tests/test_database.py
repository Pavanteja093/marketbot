import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "market_intelligence.db"

print("=" * 60)
print("DATABASE TEST")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name;
""")

tables = cursor.fetchall()

print(f"\nTables Found: {len(tables)}\n")

for table in tables:
    print(table[0])

conn.close()

print("\nDatabase test complete.")