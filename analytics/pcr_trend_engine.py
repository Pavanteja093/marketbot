import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

query = """

WITH latest AS (

    SELECT
        symbol,
        MAX(trade_time) AS latest_time

    FROM option_chain_history

    GROUP BY symbol

),

previous AS (

    SELECT
        symbol,
        MIN(trade_time) AS previous_time

    FROM (

        SELECT DISTINCT
            symbol,
            trade_time

        FROM option_chain_history

    )

    GROUP BY symbol

)

SELECT
    o.symbol,
    ROUND(AVG(o.pcr), 2) AS current_pcr

FROM option_chain_history o

JOIN latest l
ON o.symbol = l.symbol
AND o.trade_time = l.latest_time

GROUP BY o.symbol

"""

current_df = pd.read_sql(query, conn)

print("\n" + "="*60)
print("PCR TREND ANALYSIS")
print("="*60)

for _, row in current_df.iterrows():

    symbol = row["symbol"]
    current_pcr = row["current_pcr"]

    old_query = f"""

    SELECT
        ROUND(AVG(pcr),2) AS old_pcr

    FROM option_chain_history

    WHERE symbol='{symbol}'
      AND trade_time = (

            SELECT MIN(trade_time)

            FROM option_chain_history

            WHERE symbol='{symbol}'
      )

    """

    old_pcr = pd.read_sql(old_query, conn).iloc[0]["old_pcr"]

    change = round(current_pcr - old_pcr, 2)

    if change > 0.10:
        trend = "RISING"
        interpretation = "BULLISH SENTIMENT BUILDING"

    elif change < -0.10:
        trend = "FALLING"
        interpretation = "BEARISH SENTIMENT BUILDING"

    else:
        trend = "STABLE"
        interpretation = "NO MAJOR CHANGE"

    print("\n" + "="*60)
    print(symbol)
    print("="*60)

    print(f"Current PCR : {current_pcr}")
    print(f"Old PCR     : {old_pcr}")
    print(f"Change      : {change}")
    print(f"Trend       : {trend}")
    print()
    print(f"Interpretation : {interpretation}")

conn.close()