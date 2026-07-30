import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

# ----------------------------------
# ENTER DAILY DATA HERE
# ----------------------------------

data = {
    "trade_date": "2026-06-05",

    "fii_buy": 100000,
    "fii_sell": 97500,

    "dii_buy": 85000,
    "dii_sell": 87000
}

# ----------------------------------
# CALCULATE NET
# ----------------------------------

data["fii_net"] = (
    data["fii_buy"] -
    data["fii_sell"]
)

data["dii_net"] = (
    data["dii_buy"] -
    data["dii_sell"]
)

# ----------------------------------
# SAVE
# ----------------------------------

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cursor.execute(
    """
    INSERT INTO fii_dii_daily
    (
        trade_date,

        fii_buy,
        fii_sell,
        fii_net,

        dii_buy,
        dii_sell,
        dii_net
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
        data["trade_date"],

        data["fii_buy"],
        data["fii_sell"],
        data["fii_net"],

        data["dii_buy"],
        data["dii_sell"],
        data["dii_net"]
    )
)

conn.commit()
conn.close()

print("Saved Successfully")
   