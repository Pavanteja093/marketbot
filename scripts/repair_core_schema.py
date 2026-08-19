import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

conn.execute("""
CREATE TABLE IF NOT EXISTS market_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    spot_price REAL DEFAULT 0,
    avg_iv REAL DEFAULT 0,
    iv_regime TEXT DEFAULT 'UNKNOWN',
    strategy TEXT DEFAULT '',
    real_pcr REAL DEFAULT 0,
    support REAL DEFAULT 0,
    resistance REAL DEFAULT 0,
    max_pain REAL DEFAULT 0,
    delta REAL DEFAULT 0,
    gamma REAL DEFAULT 0,
    theta REAL DEFAULT 0,
    vega REAL DEFAULT 0,
    market_bias TEXT DEFAULT 'NEUTRAL',
    confidence REAL DEFAULT 0,
    expected_move REAL DEFAULT 0,
    reward_risk REAL DEFAULT 0,
    market_location TEXT DEFAULT 'UNKNOWN',
    trade_quality REAL DEFAULT 0,
    UNIQUE(trade_time, symbol)
)
""")

conn.commit()
conn.close()

print("CORE FEATURE STORE: READY")
