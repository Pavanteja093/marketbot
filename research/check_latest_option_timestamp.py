# research/check_latest_option_timestamp.py

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""

SELECT
    symbol,
    MAX(trade_time),
    MAX(spot_price)

FROM option_chain_history

GROUP BY symbol

""")

for row in cursor.fetchall():
    print(row)

conn.close()