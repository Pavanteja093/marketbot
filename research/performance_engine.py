import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

# ============================================================
# LATEST SNAPSHOT
# ============================================================

query = """

SELECT *
FROM option_chain_history

WHERE trade_time IN (

    SELECT MAX(trade_time)
    FROM option_chain_history o2
    WHERE o2.symbol = option_chain_history.symbol

)

"""

df = pd.read_sql(query, conn)

print("\n" + "="*60)
print("PERFORMANCE ENGINE")
print("="*60)

for symbol in df["symbol"].unique():

    temp = df[df["symbol"] == symbol]

    spot_price = temp["spot_price"].iloc[0]

    total_put = temp["put_oi"].sum()
    total_call = temp["call_oi"].sum()

    pcr = round(total_put / total_call, 2)

    support_row = temp.loc[temp["put_oi"].idxmax()]
    resistance_row = temp.loc[temp["call_oi"].idxmax()]

    support = int(support_row["strike"])
    resistance = int(resistance_row["strike"])

    range_width = resistance - support

    # ========================================================
    # REGIME
    # ========================================================

    if range_width <= 1000:

        regime = "RANGEBOUND"

    elif range_width <= 3000:

        regime = "NEUTRAL"

    else:

        regime = "VOLATILE"

    # ========================================================
    # STRATEGY
    # ========================================================

    confidence = 50

    if regime == "RANGEBOUND":

        strategy = "IRON CONDOR"
        confidence += 20

    elif regime == "VOLATILE":

        strategy = "LONG STRANGLE"
        confidence += 15

    else:

        strategy = "WAIT"

    if pcr > 1.1:

        confidence += 10

    elif pcr < 0.8:

        confidence += 10

    confidence = min(confidence, 95)

    max_pain = round(
        temp["strike"].median()
    )

    # ========================================================
    # SAVE SIGNAL
    # ========================================================

    conn.execute("""

    INSERT INTO signal_performance (

        signal_time,
        symbol,
        spot_price,

        pcr,

        support,
        resistance,

        max_pain,

        regime,
        strategy,

        confidence

    )

    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        temp["trade_time"].iloc[0],
        symbol,
        float(spot_price),

        float(pcr),

        support,
        resistance,

        float(max_pain),

        regime,
        strategy,

        float(confidence)

    ))

    print(
        f"Saved signal for {symbol}"
    )

conn.commit()
conn.close()

print("\nDone.")