import sqlite3

conn = sqlite3.connect("market_intelligence.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS option_chain_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_time TIMESTAMP,

    symbol TEXT,

    expiry DATE,

    strike REAL,

    call_ltp REAL,
    put_ltp REAL,

    call_oi INTEGER,
    put_oi INTEGER,

    call_change_oi INTEGER,
    put_change_oi INTEGER,

    call_volume INTEGER,
    put_volume INTEGER,

    pcr REAL,

    spot_price REAL

)
""")

conn.commit()

print("option_chain_history created successfully")

conn.close()