import sqlite3

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

columns = [

    "call_iv REAL",
    "put_iv REAL",

    "call_delta REAL",
    "put_delta REAL",

    "call_gamma REAL",
    "put_gamma REAL",

    "call_theta REAL",
    "put_theta REAL",

    "call_vega REAL",
    "put_vega REAL",

    "call_pop REAL",
    "put_pop REAL"

]

for col in columns:

    try:

        cursor.execute(
            f"ALTER TABLE option_chain_history ADD COLUMN {col}"
        )

        print("Added:", col)

    except:

        print("Exists:", col)

conn.commit()
conn.close()