"""Safe compatibility entry point for the adaptive-learning stage.

The current Track-A validation explicitly reports that learning_history has
zero valid source records. This module therefore refuses to invent learned
weights or predictions and reports the data-gated state.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "market_intelligence.db"

def run():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='learning_history'"
        ).fetchone()
        if not row[0]:
            print("LEARNING ENGINE: DATA-GATED (learning_history table absent)")
            return {"status": "DATA_GATED", "rows": 0}
        rows = conn.execute("SELECT COUNT(*) FROM learning_history").fetchone()[0]
    finally:
        conn.close()

    if rows == 0:
        print("LEARNING ENGINE: DATA-GATED (learning_history is empty)")
        return {"status": "DATA_GATED", "rows": 0}

    print(f"LEARNING ENGINE: {rows:,} learning records available")
    return {"status": "READY", "rows": rows}

def learning_engine():
    return run()

if __name__ == "__main__":
    run()
