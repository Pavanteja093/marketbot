import sqlite3
from datetime import datetime

import pandas as pd
import yfinance as yf


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

print("Database Path:", DB_PATH)


INDEX_MAP = {
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
}


def fetch_index_data(index_name, symbol):

    df = yf.download(
        symbol,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if len(df) < 2:
        return None

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    close_price = float(latest["Close"].iloc[0])
    previous_close = float(previous["Close"].iloc[0])

    change_pct = (
        (close_price - previous_close)
        / previous_close
    ) * 100

    trade_date = pd.to_datetime(latest.name).date()

    print(type(latest.name))
    print(latest.name)

    print(f"\nDownloading {index_name} ({symbol})")

    df = yf.download(
        symbol,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    print(df)

    print("Rows:", len(df))

    if len(df) < 2:
        print("Not enough rows")
        return None

    return {

        "trade_date": trade_date,

        "index_name": index_name,

        "open": float(latest["Open"].iloc[0]),
        "high": float(latest["High"].iloc[0]),
        "low": float(latest["Low"].iloc[0]),

        "previous_close": previous_close,
        "close": close_price,

        "price_change": round(
            close_price - previous_close,
            2
        ),

        "change_pct": round(
            change_pct,
            2
        )

    }    


def save_to_db(data):

    conn = sqlite3.connect(str(DB_PATH))

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO indices_daily
        (
            trade_date,
            index_name,

            open,
            high,
            low,

            previous_close,
            close,

            price_change,
            change_pct
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["trade_date"],
            data["index_name"],

            data["open"],
            data["high"],
            data["low"],

            data["previous_close"],
            data["close"],

            data["price_change"],
            data["change_pct"]
        )
    )

    conn.commit()
    conn.close()


def main():

    for index_name, symbol in INDEX_MAP.items():

        data = fetch_index_data(index_name, symbol)

        if data:
            save_to_db(data)
            print(f"Saved: {index_name}")

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    main()
