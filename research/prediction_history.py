"""Compatibility stage for the retired standalone prediction-history module."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "market_intelligence.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prediction_history'"
        ).fetchone()
        if not exists:
            raise RuntimeError("prediction_history table does not exist")
        rows = conn.execute("SELECT COUNT(*) FROM prediction_history").fetchone()[0]
        print(f"Prediction History Compatibility Check: {rows:,} rows available")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
