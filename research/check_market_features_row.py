import sqlite3

conn = sqlite3.connect("market_intelligence.db")

row = conn.execute("""
SELECT *
FROM market_features
WHERE symbol='NIFTY'
ORDER BY trade_time DESC
LIMIT 1
""").fetchone()

print(row)

conn.close()