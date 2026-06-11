import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

# ----------------------------------
# GET LAST 2 TRADING DAYS
# ----------------------------------

dates = pd.read_sql(
    """
    SELECT DISTINCT trade_date
    FROM stocks_daily
    ORDER BY trade_date DESC
    LIMIT 2
    """,
    conn
)

if len(dates) < 2:

    print("Not enough historical data.")
    conn.close()
    exit()

latest_date = dates.iloc[0]["trade_date"]
previous_date = dates.iloc[1]["trade_date"]

# ----------------------------------
# GET TOP STOCKS FROM LATEST DAY
# ----------------------------------

query = f"""
SELECT
    symbol,
    close,
    change_pct
FROM stocks_daily
WHERE trade_date = '{latest_date}'
"""

latest_df = pd.read_sql(query, conn)

# Top momentum stocks

top_stocks = (
    latest_df
    .sort_values(
        by="change_pct",
        ascending=False
    )
    .head(10)
)

# ----------------------------------
# COMPARE TO PREVIOUS DAY
# ----------------------------------

results = []

for _, row in top_stocks.iterrows():

    symbol = row["symbol"]

    latest_close = row["close"]

    prev_query = f"""
    SELECT close
    FROM stocks_daily
    WHERE trade_date = '{previous_date}'
    AND symbol = '{symbol}'
    """

    prev_df = pd.read_sql(
        prev_query,
        conn
    )

    if len(prev_df) == 0:
        continue

    prev_close = float(
        prev_df.iloc[0]["close"]
    )

    return_pct = round(
        (
            (latest_close - prev_close)
            / prev_close
        ) * 100,
        2
    )

    results.append(
        [
            symbol,
            prev_close,
            latest_close,
            return_pct
        ]
    )

conn.close()

perf_df = pd.DataFrame(
    results,
    columns=[
        "Symbol",
        "Prev Close",
        "Latest Close",
        "Return %"
    ]
)

# ----------------------------------
# STATS
# ----------------------------------

winners = len(
    perf_df[
        perf_df["Return %"] > 0
    ]
)

losers = len(
    perf_df[
        perf_df["Return %"] <= 0
    ]
)

win_rate = round(
    winners / len(perf_df) * 100,
    2
)

avg_return = round(
    perf_df["Return %"].mean(),
    2
)

best_stock = (
    perf_df.sort_values(
        by="Return %",
        ascending=False
    )
    .iloc[0]
)

worst_stock = (
    perf_df.sort_values(
        by="Return %",
        ascending=True
    )
    .iloc[0]
)

# ----------------------------------
# OUTPUT
# ----------------------------------

print("\n" + "=" * 60)
print("PERFORMANCE TRACKER")
print("=" * 60)

print(
    f"\nPeriod : "
    f"{previous_date} -> {latest_date}"
)

print(
    f"Stocks Tracked : "
    f"{len(perf_df)}"
)

print(
    f"Winners : "
    f"{winners}"
)

print(
    f"Losers : "
    f"{losers}"
)

print(
    f"Win Rate : "
    f"{win_rate}%"
)

print(
    f"Average Return : "
    f"{avg_return}%"
)

print("\nBEST PERFORMER")

print(
    f"{best_stock['Symbol']} "
    f"({best_stock['Return %']}%)"
)

print("\nWORST PERFORMER")

print(
    f"{worst_stock['Symbol']} "
    f"({worst_stock['Return %']}%)"
)

print("\nTOP STOCK RETURNS")

print(
    perf_df.to_string(
        index=False
    )
)