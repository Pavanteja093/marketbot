import sqlite3
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
DB_PATH=BASE_DIR/"market_intelligence.db"
conn=sqlite3.connect(DB_PATH)
print("="*78); print("MARKETBOT — PHASE 2 PREDICTION / OUTCOME INVENTORY"); print("="*78)
tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
for name in ["signal_performance","signal_history","signal_history_v2","prediction_history","outcome_tracker","trade_performance","daily_recommendations"]:
    print(f"{name:24}: {'EXISTS' if name in tables else 'MISSING'}")
    if name in tables:
        try: print(f"  ROWS: {conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]}")
        except Exception as e: print("  ERROR:",e)
if "signal_performance" in tables:
    print("\nColumns:",[r[1] for r in conn.execute("PRAGMA table_info(signal_performance)")])
    for r in conn.execute("SELECT * FROM signal_performance ORDER BY id DESC LIMIT 10"): print(r)
conn.close()
