import sqlite3
import pandas as pd


def portfolio_simulator():

    conn = sqlite3.connect("market_intelligence.db")

    df = pd.read_sql("""

        SELECT

            trade_date,

            future_return_5d

        FROM prediction_history

        WHERE future_return_5d IS NOT NULL

        ORDER BY trade_date

    """, conn)

    conn.close()

    if df.empty:

        print("\nNo portfolio history.")

        return

    capital = 1000000

    peak = capital

    max_drawdown = 0

    wins = 0

    losses = 0

    equity = []

    for r in df["future_return_5d"]:

        capital *= (1 + r / 100)

        equity.append(capital)

        if r > 0:

            wins += 1

        else:

            losses += 1

        peak = max(peak, capital)

        drawdown = (peak - capital) / peak * 100

        max_drawdown = max(max_drawdown, drawdown)

    print("\n" + "=" * 60)

    print("PORTFOLIO SIMULATION")

    print("=" * 60)

    print(f"Initial Capital : ₹1,000,000")

    print(f"Final Capital   : ₹{capital:,.2f}")

    print(f"Trades          : {len(df)}")

    print(f"Wins            : {wins}")

    print(f"Losses          : {losses}")

    print(f"Win Rate        : {wins / len(df) * 100:.2f}%")

    print(f"Max Drawdown    : {max_drawdown:.2f}%")