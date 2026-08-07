import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def add_column(sql, name):
    try:
        cursor.execute(sql)
        print(f"Added {name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"{name} already exists")
        else:
            raise


add_column(
    "ALTER TABLE factor_history ADD COLUMN volatility_score REAL",
    "volatility_score"
)

add_column(
    "ALTER TABLE factor_history ADD COLUMN volatility_grade TEXT",
    "volatility_grade"
)

add_column(
    "ALTER TABLE factor_history ADD COLUMN liquidity_score REAL",
    "liquidity_score"
)

add_column(
    "ALTER TABLE factor_history ADD COLUMN liquidity_grade TEXT",
    "liquidity_grade"
)

conn.commit()
conn.close()

print("\nMigration Complete")