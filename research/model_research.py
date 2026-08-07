import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

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
"""

df = pd.read_sql(query, conn)

conn.close()

# ----------------------------------
# MODEL A
# Current Model
# ----------------------------------

df["model_a"] = (
    df["change_pct"].rank(pct=True) * 40 +
    df["volume"].rank(pct=True) * 30
)

# ----------------------------------
# MODEL B
# Price Dominant
# ----------------------------------

df["model_b"] = (
    df["change_pct"].rank(pct=True) * 70
)

# ----------------------------------
# MODEL C
# Pure Momentum
# ----------------------------------

df["model_c"] = (
    df["change_pct"].rank(pct=True) * 100
)

# ----------------------------------
# TOP PICKS
# ----------------------------------

top_a = (
    df.sort_values(
        "model_a",
        ascending=False
    )
    .head(10)
)

top_b = (
    df.sort_values(
        "model_b",
        ascending=False
    )
    .head(10)
)

top_c = (
    df.sort_values(
        "model_c",
        ascending=False
    )
    .head(10)
)

print("\n" + "=" * 70)
print("MODEL RESEARCH")
print("=" * 70)

print("\nMODEL A (Current)")

print(
    top_a[
        ["symbol", "model_a"]
    ]
    .to_string(index=False)
)

print("\nMODEL B (Price Dominant)")

print(
    top_b[
        ["symbol", "model_b"]
    ]
    .to_string(index=False)
)

print("\nMODEL C (Pure Momentum)")

print(
    top_c[
        ["symbol", "model_c"]
    ]
    .to_string(index=False)
)