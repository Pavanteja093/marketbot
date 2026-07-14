import sqlite3
from pathlib import Path

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
# DATABASE
# --------------------------------------------------

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("\nDownloading 1 year history...")

# --------------------------------------------------
# DOWNLOAD HISTORY
# --------------------------------------------------

df = yf.download(
    WATCHLIST,
    period="1y",
    interval="1d",
    auto_adjust=False,
    progress=True,
    threads=True
)

saved_count = 0

# --------------------------------------------------
# PROCESS EACH STOCK
# --------------------------------------------------

for symbol in WATCHLIST:

    try:

        stock_df = df.xs(
            symbol,
            level=1,
            axis=1
        )

        stock_df = stock_df.dropna()

        if len(stock_df) < 2:
            continue

        stock_df = stock_df.sort_index()

        for i in range(1, len(stock_df)):

            current = stock_df.iloc[i]
            previous = stock_df.iloc[i - 1]

            trade_date = stock_df.index[i].date()

            close_price = float(current["Close"])
            previous_close = float(previous["Close"])

            price_change = (
                close_price -
                previous_close
            )

            change_pct = (
                price_change /
                previous_close
            ) * 100

            cursor.execute(
                """
                INSERT OR IGNORE INTO stocks_daily
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
                    trade_date,
                    symbol,
                    round(float(current["Open"]), 2),
                    round(float(current["High"]), 2),
                    round(float(current["Low"]), 2),
                    round(previous_close, 2),
                    round(close_price, 2),
                    round(price_change, 2),
                    int(current["Volume"]),
                    round(change_pct, 2)
                )
            )

            saved_count += 1

    except Exception as e:

        print(f"Skipped: {symbol}")
        print(e)

# --------------------------------------------------
# SAVE
# --------------------------------------------------

conn.commit()
conn.close()

print(
    f"\nSaved {saved_count} historical records."
)