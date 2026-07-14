import sqlite3

conn = sqlite3.connect("market_intelligence.db")

count = conn.execute(
    """
    SELECT COUNT(*)
    FROM factor_history
    """
).fetchone()[0]

print(count)

conn.close()