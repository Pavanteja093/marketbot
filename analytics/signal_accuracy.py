import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

# ----------------------------------
# SIGNAL DATES
# ----------------------------------

dates = pd.read_sql(
    """
    SELECT DISTINCT trade_date
    FROM signal_history
    ORDER BY trade_date
    """,
    conn
)

if len(dates) < 2:

    print("\nNot enough signal history.")
    conn.close()
    exit()

signal_date = dates.iloc[-2]["trade_date"]
evaluation_date = dates.iloc[-1]["trade_date"]

# ----------------------------------
# SIGNALS
# ----------------------------------

signals = pd.read_sql(
    f"""
    SELECT
        rank,
        symbol,
        sector,
        score
    FROM signal_history
    WHERE trade_date = '{signal_date}'
    """,
    conn
)

# ----------------------------------
# ENTRY PRICES
# ----------------------------------

entry = pd.read_sql(
    f"""
    SELECT
        symbol,
        close AS entry_price
    FROM stocks_daily
    WHERE trade_date = '{signal_date}'
    """,
    conn
)

# ----------------------------------
# EXIT PRICES
# ----------------------------------

exit_prices = pd.read_sql(
    f"""
    SELECT
        symbol,
        close AS exit_price
    FROM stocks_daily
    WHERE trade_date = '{evaluation_date}'
    """,
    conn
)

conn.close()

# ----------------------------------
# MERGE
# ----------------------------------

df = signals.merge(
    entry,
    on="symbol",
    how="left"
)

df = df.merge(
    exit_prices,
    on="symbol",
    how="left"
)

df["return_pct"] = (
    (
        df["exit_price"] -
        df["entry_price"]
    )
    /
    df["entry_price"]
) * 100

df["return_pct"] = (
    df["return_pct"]
    .round(2)
)

# ----------------------------------
# STATS
# ----------------------------------

signals_evaluated = len(df)

winners = (
    df["return_pct"] > 0
).sum()

losers = (
    df["return_pct"] <= 0
).sum()

win_rate = round(
    winners /
    signals_evaluated *
    100,
    2
)

avg_return = round(
    df["return_pct"].mean(),
    2
)

best_stock = (
    df.sort_values(
        "return_pct",
        ascending=False
    )
    .iloc[0]
)

worst_stock = (
    df.sort_values(
        "return_pct"
    )
    .iloc[0]
)

# ----------------------------------
# OUTPUT
# ----------------------------------

print("\n" + "=" * 70)
print("SIGNAL ACCURACY")
print("=" * 70)

print(
    f"\nSignal Date     : {signal_date}"
)

print(
    f"Evaluation Date : {evaluation_date}"
)

print(
    f"\nSignals Evaluated : "
    f"{signals_evaluated}"
)

print(
    f"Winners : {winners}"
)

print(
    f"Losers : {losers}"
)

print(
    f"Win Rate : {win_rate}%"
)

print(
    f"Average Return : {avg_return}%"
)

print("\nBEST SIGNAL")

print(
    f"{best_stock['symbol']} "
    f"({best_stock['return_pct']}%)"
)

print("\nWORST SIGNAL")

print(
    f"{worst_stock['symbol']} "
    f"({worst_stock['return_pct']}%)"
)

print("\nDETAILS")

print(
    df[
        [
            "rank",
            "symbol",
            "sector",
            "return_pct"
        ]
    ]
    .sort_values(
        "rank"
    )
    .to_string(index=False)
)