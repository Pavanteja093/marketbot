import sqlite3

conn = sqlite3.connect("market_intelligence.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS factor_library (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    symbol TEXT,

    position_52w REAL,
    breakout_distance REAL,
    volume_expansion REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, symbol)
)
""")

conn.commit()
conn.close()

print("factor_library created")