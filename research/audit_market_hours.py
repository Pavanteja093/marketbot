import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql("""

SELECT trade_time
FROM option_chain_history

""", conn)

conn.close()

df["trade_time"] = pd.to_datetime(
    df["trade_time"],
     format="mixed",
    errors= "coerce"
)
df=df.dropna(
    subset=["trade_time"]
)


market_open = pd.to_datetime("09:15").time()
market_close = pd.to_datetime("15:30").time()

df["is_market_hours"] = df["trade_time"].dt.time.between(
    market_open,
    market_close
)

total_rows = len(df)

market_rows = len(
    df[df["is_market_hours"]]
)

after_hours_rows = total_rows - market_rows

print("\nMARKET HOURS AUDIT")
print("=" * 60)

print("Total Rows        :", total_rows)
print("Market Hour Rows  :", market_rows)
print("After Hour Rows   :", after_hours_rows)

if total_rows > 0:

    print(
        "Market Hour %",
        round(
            market_rows / total_rows * 100,
            2
        )
    )