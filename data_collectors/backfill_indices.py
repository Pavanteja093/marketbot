import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


INDEXES = {
    "NIFTY50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}


def download_index(index_name, symbol):

    print(f"\nDownloading {index_name} ({symbol})")

    df = yf.download(
        symbol,
        period="1y",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if not isinstance(df, pd.DataFrame):
        print(f"{index_name}: invalid download result")
        return None

    if df.empty:
        print(f"{index_name}: no data")
        return None

    # yfinance can return MultiIndex columns.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        print(
            f"{index_name}: missing columns: {missing}"
        )
        return None

    df = df.dropna(
        subset=required_columns
    ).copy()

    if df.empty:
        print(f"{index_name}: no valid rows")
        return None

    df = df.sort_index()

    return df


def build_records(index_name, df):

    records = []

    previous_close = None

    for date, row in df.iterrows():

        close_price = float(row["Close"])

        if previous_close is None:
            price_change = 0.0
            change_pct = 0.0
            previous_value = None

        else:
            price_change = (
                close_price
                - previous_close
            )

            change_pct = (
                price_change
                / previous_close
            ) * 100

            previous_value = previous_close

        records.append(
            (
                str(
                    pd.to_datetime(date).date()
                ),
                index_name,

                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),

                previous_value,
                close_price,

                round(price_change, 2),
                round(change_pct, 2),
            )
        )

        previous_close = close_price

    return records


def backfill_indices():

    print("\n" + "=" * 70)
    print("MARKETBOT INDEX HISTORICAL BACKFILL")
    print("=" * 70)

    conn = sqlite3.connect(str(DB_PATH))

    total_rows = 0

    for index_name, symbol in INDEXES.items():

        df = download_index(
            index_name,
            symbol
        )

        if df is None:
            continue

        records = build_records(
            index_name,
            df
        )

        if not records:
            print(
                f"{index_name}: no records generated"
            )
            continue

        conn.executemany(
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
            records,
        )

        conn.commit()

        total_rows += len(records)

        print(
            f"{index_name}: "
            f"{len(records)} rows saved"
        )

        print(
            f"Date range: "
            f"{records[0][0]} -> "
            f"{records[-1][0]}"
        )

    conn.close()

    print("\n" + "=" * 70)
    print(
        f"TOTAL INDEX ROWS PROCESSED: "
        f"{total_rows:,}"
    )
    print("=" * 70)


if __name__ == "__main__":
    backfill_indices()