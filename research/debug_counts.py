import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

count_all = conn.execute(
    """
    SELECT COUNT(*)
    FROM prediction_history
    """
).fetchone()[0]

count_scores = conn.execute(
    """
    SELECT COUNT(intelligence_score)
    FROM prediction_history
    """
).fetchone()[0]

print("Rows:", count_all)
print("Scores:", count_scores)

conn.close()