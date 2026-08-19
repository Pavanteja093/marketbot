"""Compatibility sector-strength API used by legacy reports."""
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

def get_sector_strength():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        stocks = pd.read_sql("""
            SELECT symbol, change_pct
            FROM stocks_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM stocks_daily)
        """, conn)
    finally:
        conn.close()

    try:
        from analytics.sector_mapping import SECTORS
    except Exception:
        SECTORS = {}

    rows = []
    for sector, members in SECTORS.items():
        x = stocks[stocks["symbol"].isin(members)]
        if not x.empty:
            rows.append([sector, float(x["change_pct"].mean())])

    return pd.DataFrame(rows, columns=["Sector", "Strength"]).sort_values(
        "Strength", ascending=False
    ).reset_index(drop=True)
