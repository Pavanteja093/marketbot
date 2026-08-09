import sqlite3
import pandas as pd


def trade_planner():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT

            symbol,

            close,

            intelligence_score,

            volatility_score

        FROM factor_history

        WHERE trade_date=(

            SELECT MAX(trade_date)

            FROM factor_history

        )

    """, conn)

    conn.close()

    if df.empty:

        print("No trade data.")

        return

    df["entry"] = df["close"]

    df["stop_loss"] = (

        df["close"]

        -

        df["volatility_score"]*0.75

    ).round(2)

    risk = (

        df["entry"]

        -

        df["stop_loss"]

    )

    df["target"] = (
        df["entry"] * 1.05
    ).round(2)

    risk = df["entry"] - df["stop_loss"]

    df["risk_reward"] = (
        (
            df["target"] - df["entry"]
        )
        / risk.replace(0, float("nan"))
    ).round(2)

    print("\nTRADE PLAN")
    print("=" * 70)

    print(
        df[
            [
                "symbol",
                "entry",
                "stop_loss",
                "target",
                "risk_reward"
            ]
        ].head(20)
    )