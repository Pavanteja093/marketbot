import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

# -----------------------------------------------------
# IV ANALYSIS
# -----------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS iv_analysis (

    trade_time TEXT,

    symbol TEXT,

    avg_call_iv REAL,

    avg_put_iv REAL,

    avg_iv REAL,

    iv_regime TEXT,

    recommended_strategy TEXT,

    PRIMARY KEY (trade_time, symbol)
)
""")

# -----------------------------------------------------
# PCR ANALYSIS
# -----------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS pcr_analysis (

    trade_time TEXT,

    symbol TEXT,

    pcr REAL,

    interpretation TEXT,

    PRIMARY KEY (trade_time, symbol)
)
""")

# -----------------------------------------------------
# OI ANALYSIS
# -----------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS oi_analysis (

    trade_time TEXT,

    symbol TEXT,

    support REAL,

    resistance REAL,

    max_pain REAL,

    PRIMARY KEY (trade_time, symbol)
)
""")

conn.commit()

conn.close()

print("Analysis tables created successfully.")