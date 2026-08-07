import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS market_features (

    trade_time TEXT,

    symbol TEXT,

    spot_price REAL,

    avg_iv REAL,

    iv_regime TEXT,

    strategy TEXT,

    real_pcr REAL,

    support REAL,

    resistance REAL,

    max_pain REAL,

    delta REAL,

    gamma REAL,

    theta REAL,

    vega REAL,

    market_bias TEXT,

    confidence INTEGER,

    PRIMARY KEY (trade_time, symbol)

)
""")

conn.commit()
conn.close()

print("Feature Store Created.")