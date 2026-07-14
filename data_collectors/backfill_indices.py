import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


INDEXES = {
    "NIFTY50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN"
}


def backfill_indices():

    conn = sqlite3.connect(str(DB_PATH))

    total_rows = 0

    for index_name, symbol in INDEXES.items():

        print(f"\nDownloading {index_name}...")

        df = yf.download(
            symbol,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if len(df) == 0:
            continue

        df = df.reset_index()

        df.columns = [
            col[0] if isinstance(col, tuple) else col
            for col in df.columns
        ]
    
        records = []

        for _, row in df.iterrows():

            records.append(
            (
                str(
                    pd.to_datetime(
                        row["Date"]
                    ).date()
                ),
                index_name,
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                0
            )
        )

        close_price = float(row["Close"])

        records.append(
                (
                    str(row["Date"].date()),
                    index_name,
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    close_price,
                    0
                )
            )

        conn.executemany(
            """
            INSERT OR REPLACE INTO indices_daily (

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
            records
        )

        total_rows += len(records)

        print(
            f"Saved {len(records)} rows"
        )

    conn.commit()
    conn.close()

    print("\n")
    print("=" * 70)
    print(f"TOTAL ROWS SAVED: {total_rows}")
    print("=" * 70)


if __name__ == "__main__":

    backfill_indices()