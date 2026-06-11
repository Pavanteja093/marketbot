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

    close_price = float(latest["Close"])
    previous_close = float(previous["Close"])

    change_pct = (
        (close_price - previous_close)
        / previous_close
    ) * 100

    return {
        "trade_date": datetime.now().date(),
        "index_name": index_name,
        "open": float(latest["Open"]),
        "high": float(latest["High"]),
        "low": float(latest["Low"]),
        "close": close_price,
        "change_pct": round(change_pct, 2)
    }


def save_to_db(data):

    conn = sqlite3.connect(str(DB_PATH))

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO indices_daily
        (
            trade_date,
            index_name,
            open,
            high,
            low,
            close,
            change_pct
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["trade_date"],
            data["index_name"],
            data["open"],
            data["high"],
            data["low"],
            data["close"],
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


if __name__ == "__main__":
    main()