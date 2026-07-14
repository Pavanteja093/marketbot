import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

# ============================================================
# LOAD MARKET DATA
# ============================================================

query = """

SELECT
    trade_time,
    symbol,
    spot_price,

    SUM(put_oi) AS total_put_oi,
    SUM(call_oi) AS total_call_oi

FROM option_chain_history

GROUP BY
    trade_time,
    symbol

ORDER BY trade_time

"""

df = pd.read_sql(query, conn)

print("\n" + "="*60)
print("BACKTEST ENGINE")
print("="*60)

results = []

for symbol in df["symbol"].unique():

    temp = df[df["symbol"] == symbol].copy()

    temp["pcr"] = (
        temp["total_put_oi"]
        / temp["total_call_oi"]
    )

    temp["future_price"] = (
        temp["spot_price"]
        .shift(-1)
    )

    temp = temp.dropna()

    correct = 0
    total = 0

    for _, row in temp.iterrows():

        pcr = row["pcr"]

        current_price = row["spot_price"]
        future_price = row["future_price"]

        # ----------------------------------------------------
        # SIGNAL LOGIC
        # ----------------------------------------------------

        if pcr > 1.1:

            prediction = "UP"

        elif pcr < 0.8:

            prediction = "DOWN"

        else:

            prediction = "NEUTRAL"

        # ----------------------------------------------------
        # ACTUAL RESULT
        # ----------------------------------------------------

        if future_price > current_price:

            actual = "UP"

        elif future_price < current_price:

            actual = "DOWN"

        else:

            actual = "NEUTRAL"
        
        print(
            symbol,
            round(pcr, 2),
            prediction,
            actual,
            current_price,
            future_price
        )

        if prediction == actual:

            correct += 1

        total += 1

    accuracy = round(
        correct / total * 100,
        2
    )

    results.append(
        [symbol, accuracy, total]
    )

# ============================================================
# OUTPUT
# ============================================================

result_df = pd.DataFrame(
    results,
    columns=[
        "Symbol",
        "Accuracy %",
        "Samples"
    ]
)

print()
print(result_df)

conn.close()