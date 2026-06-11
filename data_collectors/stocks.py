import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import yfinance as yf

# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

# --------------------------------------------------
# LOAD STOCK LIST
# --------------------------------------------------

stocks_df = pd.read_csv(
    BASE_DIR / "data" / "nifty50.csv"
)

WATCHLIST = stocks_df["symbol"].tolist()

# --------------------------------------------------
# DATABASE SAVE
# --------------------------------------------------

def save_to_db(data):

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO stocks_daily
        (
            trade_date,
            symbol,
            open,
            high,
            low,
            previous_close,
            close,
            price_change,
            volume,
            change_pct
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["trade_date"],
            data["symbol"],
            data["open"],
            data["high"],
            data["low"],
            data["previous_close"],
            data["close"],
            data["price_change"],
            data["volume"],
            data["change_pct"]
        )
    )

    conn.commit()
    conn.close()

# --------------------------------------------------
# FETCH STOCK DATA
# --------------------------------------------------

def fetch_stock(symbol):

    df = yf.download(
        symbol,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if len(df) < 2:
        return None

    latest = df.tail(1)
    previous = df.tail(2).head(1)


    close_price = float(latest["Close"].iloc[0])
    previous_close = float(previous["Close"].iloc[0])

    price_change = close_price - previous_close

    change_pct = (
        price_change / previous_close
    ) * 100

    return {
        "trade_date": datetime.now().date(),
        "symbol": symbol,
        "open": float(latest["Open"].iloc[0]),
        "high": float(latest["High"].iloc[0]),
        "low": float(latest["Low"].iloc[0]),
        "previous_close": round(previous_close, 2),
        "close": round(close_price, 2),
        "price_change": round(price_change, 2),
        "volume": int(latest["Volume"].iloc[0]),
        "change_pct": round(change_pct, 2)
    }

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    for stock in WATCHLIST:

        try:

            data = fetch_stock(stock)

            if data:
                save_to_db(data)
                print(f"Saved: {stock}")

        except Exception as e:

            print(f"Skipped: {stock}")
            print(e)

            print(f"Error: {stock}")
            print(e)

if __name__ == "__main__":
    main()