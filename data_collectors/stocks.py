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

def main():
    
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

    # --------------------------------------------------
    # BULK DOWNLOAD
    # --------------------------------------------------

    print("\nDownloading NIFTY stocks...")

    df = yf.download(
        WATCHLIST,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=True
    )

    today = datetime.now().date()

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

            latest = stock_df.iloc[-1]
            previous = stock_df.iloc[-2]

            close_price = float(latest["Close"])
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
                    today,
                    symbol,
                    round(float(latest["Open"]), 2),
                    round(float(latest["High"]), 2),
                    round(float(latest["Low"]), 2),
                    round(previous_close, 2),
                    round(close_price, 2),
                    round(price_change, 2),
                    int(latest["Volume"]),
                    round(change_pct, 2)
                )
            )

            saved_count += 1

        except Exception as e:

            print(
                f"Skipped: {symbol}"
            )

            print(e)

    # --------------------------------------------------
    # COMMIT ONCE
    # --------------------------------------------------

    conn.commit()
    conn.close()

    print(
        f"\nSaved {saved_count} stocks successfully."
    )


if __name__ == "__main__":

    main()