import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

print("\n" + "="*60)
print("MARKET SUMMARY")
print("="*60)

# -----------------------------
# MARKET INDICES
# -----------------------------

indices = pd.read_sql("""
SELECT
    index_name,
    open,
    high,
    low,
    close,
    change_pct
FROM indices_daily
WHERE trade_date = (
    SELECT MAX(trade_date)
    FROM indices_daily
)
""", conn)

print("\nMARKET SNAPSHOT\n")
print(indices)

# -----------------------------
# TOP GAINERS
# -----------------------------

gainers = pd.read_sql("""
SELECT DISTINCT
    symbol,
    close,
    price_change,
    change_pct
FROM stocks_daily
ORDER BY change_pct DESC
LIMIT 5
""", conn)

print("\nTOP GAINERS\n")
print(gainers)

# -----------------------------
# TOP LOSERS
# -----------------------------

losers = pd.read_sql("""
SELECT DISTINCT
    symbol,
    close,
    price_change,
    change_pct
FROM stocks_daily
ORDER BY change_pct ASC
LIMIT 5
""", conn)

print("\nTOP LOSERS\n")
print(losers)

# -----------------------------
# PRICE SHOCKERS
# -----------------------------

shockers = pd.read_sql("""
SELECT DISTINCT
    symbol,
    close,
    price_change,
    change_pct
FROM stocks_daily
WHERE ABS(change_pct) >= 1
ORDER BY ABS(change_pct) DESC
""", conn)


print("\nPRICE SHOCKERS\n")
print(shockers)

# -----------------------------
# VOLUME LEADERS
# -----------------------------

query = """
SELECT
    symbol,
    close,
    volume,
    change_pct
FROM stocks_daily
WHERE trade_date = (
    SELECT MAX(trade_date)
    FROM stocks_daily
)
ORDER BY volume DESC
LIMIT 5
"""

df = pd.read_sql(query, conn)

print("\nVOLUME LEADERS\n")
print(df)
conn.close()