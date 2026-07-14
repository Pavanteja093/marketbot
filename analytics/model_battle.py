import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def evaluate_model(
    signal_table,
    score_column
):

    conn = sqlite3.connect(str(DB_PATH))

    signal_dates = pd.read_sql(
        f"""
        SELECT DISTINCT trade_date
        FROM {signal_table}
        ORDER BY trade_date
        """,
        conn
    )

    if len(signal_dates) < 2:

        conn.close()

        return None

    results = []

    for i in range(
        len(signal_dates) - 1
    ):

        signal_date = (
            signal_dates.iloc[i]
            ["trade_date"]
        )

        evaluation_date = (
            signal_dates.iloc[i + 1]
            ["trade_date"]
        )

        signals = pd.read_sql(
            f"""
            SELECT *
            FROM {signal_table}
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
            on="symbol"
        )

        df = df.merge(
            exit_prices,
            on="symbol"
        )

        df["return_pct"] = (
            (
                df["exit_price"] -
                df["entry_price"]
            )
            /
            df["entry_price"]
        ) * 100

        results.append(df)

    conn.close()

    results = pd.concat(
        results,
        ignore_index=True
    )

    results = results.dropna(
        subset=["return_pct"]
    )

    win_rate = round(
        (
            results["return_pct"] > 0
        ).mean() * 100,
        2
    )

    avg_return = round(
        results["return_pct"].mean(),
        2
    )

    best = round(
        results["return_pct"].max(),
        2
    )

    worst = round(
        results["return_pct"].min(),
        2
    )

    return {
        "signals": len(results),
        "win_rate": win_rate,
        "avg_return": avg_return,
        "best": best,
        "worst": worst
    }


# ----------------------------------
# MODEL EVALUATION
# ----------------------------------

v1 = evaluate_model(
    "signal_history",
    "score"
)

v2 = evaluate_model(
    "signal_history_v2",
    "intelligence_score"
)

print("\n" + "=" * 70)
print("MODEL BATTLE")
print("=" * 70)

# ----------------------------------
# V1
# ----------------------------------

print("\nMODEL V1")

if v1:

    print(
        f"Signals      : "
        f"{v1['signals']}"
    )

    print(
        f"Win Rate     : "
        f"{v1['win_rate']}%"
    )

    print(
        f"Avg Return   : "
        f"{v1['avg_return']}%"
    )

    print(
        f"Best Return  : "
        f"{v1['best']}%"
    )

    print(
        f"Worst Return : "
        f"{v1['worst']}%"
    )

else:

    print(
        "Insufficient history."
    )

# ----------------------------------
# V2
# ----------------------------------

print("\nMODEL V2")

if v2:

    print(
        f"Signals      : "
        f"{v2['signals']}"
    )

    print(
        f"Win Rate     : "
        f"{v2['win_rate']}%"
    )

    print(
        f"Avg Return   : "
        f"{v2['avg_return']}%"
    )

    print(
        f"Best Return  : "
        f"{v2['best']}%"
    )

    print(
        f"Worst Return : "
        f"{v2['worst']}%"
    )

else:

    print(
        "Insufficient history."
    )

# ----------------------------------
# WINNER
# ----------------------------------

print("\nWINNER")

if v1 and v2:

    if (
        v2["avg_return"]
        >
        v1["avg_return"]
    ):

        print(
            "MODEL V2"
        )

    elif (
        v1["avg_return"]
        >
        v2["avg_return"]
    ):

        print(
            "MODEL V1"
        )

    else:

        print(
            "TIE"
        )

else:

    print(
        "Need more data."
    )