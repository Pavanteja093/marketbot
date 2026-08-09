from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "market_intelligence.db"


OPTION_CHAIN_SQL = """
CREATE TABLE IF NOT EXISTS option_chain_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_time DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    expiry DATE NOT NULL,
    strike REAL NOT NULL,

    call_ltp REAL,
    put_ltp REAL,

    call_oi REAL,
    put_oi REAL,

    call_change_oi REAL,
    put_change_oi REAL,

    call_volume INTEGER,
    put_volume INTEGER,

    pcr REAL,
    spot_price REAL,

    call_iv REAL,
    put_iv REAL,

    call_delta REAL,
    put_delta REAL,

    call_gamma REAL,
    put_gamma REAL,

    call_theta REAL,
    put_theta REAL,

    call_vega REAL,
    put_vega REAL,

    call_pop REAL,
    put_pop REAL
);
"""

SYSTEM_STATUS_SQL = """
CREATE TABLE IF NOT EXISTS system_status (
    component TEXT PRIMARY KEY,
    last_successful_write DATETIME,
    status TEXT NOT NULL
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_option_chain_lookup
ON option_chain_history (symbol, expiry, trade_time);

CREATE INDEX IF NOT EXISTS idx_option_chain_strike
ON option_chain_history (symbol, expiry, strike);
"""


def main() -> int:
    if not DB_PATH.exists():
        print(f"CRITICAL ERROR: Database does not exist: {DB_PATH}")
        return 2

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(OPTION_CHAIN_SQL)
        conn.execute(SYSTEM_STATUS_SQL)
        conn.executescript(INDEX_SQL)
        conn.commit()

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name IN "
                "('option_chain_history', 'system_status')"
            )
        }

        missing = {"option_chain_history", "system_status"} - tables
        if missing:
            print("CRITICAL ERROR: Migration did not create: " + ", ".join(sorted(missing)))
            return 2

        print("OPTION-CHAIN INFRASTRUCTURE MIGRATION")
        print("=" * 42)
        print(f"Database: {DB_PATH}")
        print("option_chain_history: CREATED/EXISTS")
        print("system_status:        CREATED/EXISTS")
        print("Existing data:        UNTOUCHED")
        print("STATUS: PASS")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
