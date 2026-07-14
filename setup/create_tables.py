import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

conn.execute("""
CREATE TABLE IF NOT EXISTS daily_recommendations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    symbol TEXT,

    regime TEXT,

    expected_return REAL,

    confidence TEXT,

    weight_pct REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS trade_performance (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    symbol TEXT,

    expected_return REAL,

    actual_return REAL,

    result TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

CREATE TABLE IF NOT EXISTS option_snapshots (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    symbol TEXT,

    expiry DATE,

    strike REAL,

    option_type TEXT,

    oi INTEGER,

    change_oi INTEGER,

    iv REAL,

    ltp REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

conn.commit()

print("Tables created successfully.")

conn.close()