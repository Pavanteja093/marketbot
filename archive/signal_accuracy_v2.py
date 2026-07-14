import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

# ----------------------------------
# GET SIGNAL DATES
# ----------------------------------

signal_dates = pd.read_sql(
    """
    SELECT DISTINCT trade_date
    FROM signal_history
    ORDER BY trade_date
    """,
    conn
)

if len(signal_dates) < 2:

    print("\nNot enough signal history.")
    conn.close()
    exit()

all_results = []

# ----------------------------------
# EVALUATE EACH SIGNAL PERIOD
# ----------------------------------

for i in range(len(signal_dates) - 1):

    signal_date = signal_dates.iloc[i]["trade_date"]
    evaluation_date = signal_dates.iloc[i + 1]["trade_date"]

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

    df["signal_date"] = signal_date
    df["evaluation_date"] = evaluation_date

    all_results.append(df)

conn.close()

# ----------------------------------
# COMBINE ALL RESULTS
# ----------------------------------

results = pd.concat(
    all_results,
    ignore_index=True
)

results = results.dropna(
    subset=["return_pct"]
)

# ----------------------------------
# OVERALL STATS
# ----------------------------------

signals_evaluated = len(results)

winners = (
    results["return_pct"] > 0
).sum()

losers = (
    results["return_pct"] <= 0
).sum()

win_rate = round(
    winners /
    signals_evaluated *
    100,
    2
)

avg_return = round(
    results["return_pct"].mean(),
    2
)

# ----------------------------------
# RANK ANALYSIS
# ----------------------------------

rank_stats = (
    results.groupby("rank")["return_pct"]
           .mean()
           .round(2)
           .reset_index()
)

# ----------------------------------
# SECTOR ANALYSIS
# ----------------------------------

sector_stats = (
    results.groupby("sector")["return_pct"]
           .mean()
           .round(2)
           .reset_index()
           .sort_values(
               "return_pct",
               ascending=False
           )
)

# ----------------------------------
# BEST / WORST SIGNAL
# ----------------------------------

best_signal = (
    results.sort_values(
        "return_pct",
        ascending=False
    )
    .iloc[0]
)

worst_signal = (
    results.sort_values(
        "return_pct"
    )
    .iloc[0]
)

# ----------------------------------
# OUTPUT
# ----------------------------------

print("\n" + "=" * 70)
print("SIGNAL ACCURACY RESEARCH")
print("=" * 70)

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
    f"Average Return : "
    f"{avg_return}%"
)

print("\nBEST SIGNAL")

print(
    f"{best_signal['symbol']} "
    f"({round(best_signal['return_pct'],2)}%)"
)

print("\nWORST SIGNAL")

print(
    f"{worst_signal['symbol']} "
    f"({round(worst_signal['return_pct'],2)}%)"
)

print("\nRANK PERFORMANCE")

print(
    rank_stats.to_string(
        index=False
    )
)

print("\nSECTOR PERFORMANCE")

print(
    sector_stats.to_string(
        index=False
    )
)