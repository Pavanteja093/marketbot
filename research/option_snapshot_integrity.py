import sqlite3

DB = "market_intelligence.db"

conn = sqlite3.connect(DB)

print("=" * 80)
print("MARKETBOT — OPTION SNAPSHOT INTEGRITY AUDIT")
print("=" * 80)

# ------------------------------------------------------------
# 1. SNAPSHOT INVENTORY
# ------------------------------------------------------------

print("\n[1] SNAPSHOT INVENTORY")
print("-" * 80)

rows = conn.execute("""
SELECT
    symbol,
    expiry,
    trade_time,
    COUNT(*) AS row_count,
    COUNT(DISTINCT strike) AS unique_strikes,
    MIN(strike),
    MAX(strike),
    MIN(spot_price),
    MAX(spot_price)
FROM option_chain_history
GROUP BY symbol, expiry, trade_time
ORDER BY trade_time DESC
LIMIT 20
""").fetchall()

for r in rows:
    print(r)


# ------------------------------------------------------------
# 2. DUPLICATES
# ------------------------------------------------------------

print("\n[2] DUPLICATE SNAPSHOT ROWS")
print("-" * 80)

rows = conn.execute("""
SELECT
    symbol,
    expiry,
    trade_time,
    strike,
    COUNT(*) AS duplicates
FROM option_chain_history
GROUP BY symbol, expiry, trade_time, strike
HAVING COUNT(*) > 1
ORDER BY trade_time DESC
""").fetchall()

print("Duplicate groups:", len(rows))

for r in rows[:20]:
    print(r)


# ------------------------------------------------------------
# 3. MISSING VALUES
# ------------------------------------------------------------

print("\n[3] MISSING VALUE AUDIT")
print("-" * 80)

columns = [
    "spot_price",
    "call_ltp",
    "put_ltp",
    "call_oi",
    "put_oi",
    "call_volume",
    "put_volume",
    "call_iv",
    "put_iv",
    "call_delta",
    "put_delta",
    "call_gamma",
    "put_gamma",
    "call_theta",
    "put_theta",
    "call_vega",
    "put_vega",
]

symbols = [
    "SENSEX",
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
]

for symbol in symbols:

    print(f"\n{symbol}")

    for column in columns:

        count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM option_chain_history
            WHERE symbol = ?
            AND {column} IS NULL
            """,
            (symbol,)
        ).fetchone()[0]

        if count:
            print(f"  {column:<20} NULL = {count}")


# ------------------------------------------------------------
# 4. IV AUDIT
# ------------------------------------------------------------

print("\n[4] IV SANITY AUDIT")
print("-" * 80)

rows = conn.execute("""
SELECT
    symbol,
    expiry,
    trade_time,
    COUNT(*) AS rows,
    MIN(call_iv),
    MAX(call_iv),
    AVG(call_iv),
    MIN(put_iv),
    MAX(put_iv),
    AVG(put_iv)
FROM option_chain_history
GROUP BY symbol, expiry, trade_time
ORDER BY trade_time DESC
LIMIT 20
""").fetchall()

for r in rows:
    print(r)


# ------------------------------------------------------------
# 5. SPOT CONSISTENCY
# ------------------------------------------------------------

print("\n[5] SPOT PRICE CONSISTENCY")
print("-" * 80)

rows = conn.execute("""
SELECT
    symbol,
    expiry,
    trade_time,
    COUNT(DISTINCT spot_price),
    MIN(spot_price),
    MAX(spot_price)
FROM option_chain_history
GROUP BY symbol, expiry, trade_time
ORDER BY trade_time DESC
LIMIT 20
""").fetchall()

for r in rows:
    print(r)


# ------------------------------------------------------------
# 6. STRIKE INTEGRITY
# ------------------------------------------------------------

print("\n[6] STRIKE INTEGRITY")
print("-" * 80)

rows = conn.execute("""
SELECT
    symbol,
    expiry,
    trade_time,
    COUNT(*) AS rows,
    COUNT(DISTINCT strike) AS unique_strikes,
    MIN(strike),
    MAX(strike)
FROM option_chain_history
GROUP BY symbol, expiry, trade_time
ORDER BY trade_time DESC
LIMIT 20
""").fetchall()

for r in rows:
    print(r)


# ------------------------------------------------------------
# 7. CURRENT ATM COVERAGE
# ------------------------------------------------------------

print("\n[7] CURRENT ATM COVERAGE")
print("-" * 80)

for symbol in symbols:

    row = conn.execute("""
    SELECT
        expiry,
        trade_time,
        spot_price,
        MIN(strike),
        MAX(strike),
        COUNT(*)
    FROM option_chain_history
    WHERE symbol = ?
      AND trade_time = (
          SELECT MAX(trade_time)
          FROM option_chain_history
          WHERE symbol = ?
      )
    GROUP BY expiry, trade_time, spot_price
    """, (symbol, symbol)).fetchone()

    print(symbol, "=>", row)


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)

conn.close()
