import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

columns = [
    ("momentum_score", "REAL"),
    ("momentum_grade", "TEXT"),
]

for column_name, column_type in columns:
    try:
        cursor.execute(
            f"ALTER TABLE factor_history ADD COLUMN {column_name} {column_type}"
        )
        print(f"Added {column_name}")
    except sqlite3.OperationalError:
        print(f"{column_name} already exists")

conn.commit()
conn.close()

print("\nMigration Complete")