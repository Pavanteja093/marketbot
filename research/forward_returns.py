import sqlite3
import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def calculate_forward_returns():

    conn = sqlite3.connect(str(DB_PATH))

    try:

        # --------------------------------------------------
        # VERIFY / CREATE FORWARD RETURNS TABLE
        # --------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS forward_returns (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                trade_date DATE,

                index_name TEXT,

                return_1d REAL,

                return_5d REAL,

                return_10d REAL,

                return_20d REAL
            )
            """
        )

        # --------------------------------------------------
        # LOAD STOCK HISTORY
        # --------------------------------------------------

        query = """
            SELECT
                trade_date,
                symbol,
                close
            FROM stocks_daily
            ORDER BY symbol, trade_date
        """

        df = pd.read_sql(query, conn)

        if df.empty:

            print("\nNo stock history found.")

            return

        # --------------------------------------------------
        # NORMALIZE DATE
        # --------------------------------------------------

        df["trade_date"] = pd.to_datetime(
            df["trade_date"]
        )

        # --------------------------------------------------
        # SORT CORRECTLY
        # --------------------------------------------------

        df = df.sort_values(
            [
                "symbol",
                "trade_date"
            ]
        ).reset_index(drop=True)

        # --------------------------------------------------
        # FUTURE PRICES
        # --------------------------------------------------

        grouped = df.groupby("symbol")["close"]

        df["close_1d"] = grouped.shift(-1)

        df["close_5d"] = grouped.shift(-5)

        df["close_10d"] = grouped.shift(-10)

        df["close_20d"] = grouped.shift(-20)

        # --------------------------------------------------
        # FORWARD RETURNS
        # --------------------------------------------------

        df["return_1d"] = (
            (
                df["close_1d"]
                -
                df["close"]
            )
            /
            df["close"]
        ) * 100

        df["return_5d"] = (
            (
                df["close_5d"]
                -
                df["close"]
            )
            /
            df["close"]
        ) * 100

        df["return_10d"] = (
            (
                df["close_10d"]
                -
                df["close"]
            )
            /
            df["close"]
        ) * 100

        df["return_20d"] = (
            (
                df["close_20d"]
                -
                df["close"]
            )
            /
            df["close"]
        ) * 100

        # --------------------------------------------------
        # RENAME SYMBOL -> INDEX_NAME
        # --------------------------------------------------

        df["index_name"] = df["symbol"]

        # --------------------------------------------------
        # BUILD FINAL DATASET
        # --------------------------------------------------

        result = df[
            [
                "trade_date",
                "index_name",
                "return_1d",
                "return_5d",
                "return_10d",
                "return_20d"
            ]
        ].copy()

        # --------------------------------------------------
        # ROUND RETURNS
        # --------------------------------------------------

        result["return_1d"] = result["return_1d"].round(4)

        result["return_5d"] = result["return_5d"].round(4)

        result["return_10d"] = result["return_10d"].round(4)

        result["return_20d"] = result["return_20d"].round(4)

        # --------------------------------------------------
        # REMOVE OLD DATA
        # --------------------------------------------------

        conn.execute(
            "DELETE FROM forward_returns"
        )

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        result.to_sql(
            "forward_returns",
            conn,
            if_exists="append",
            index=False
        )

        conn.commit()

        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        usable_1d = result["return_1d"].notna().sum()

        usable_5d = result["return_5d"].notna().sum()

        usable_10d = result["return_10d"].notna().sum()

        usable_20d = result["return_20d"].notna().sum()

        print("\n" + "=" * 70)

        print("FORWARD RETURNS")

        print("=" * 70)

        print(
            f"Total records      : {len(result)}"
        )

        print(
            f"Usable 1D returns  : {usable_1d}"
        )

        print(
            f"Usable 5D returns  : {usable_5d}"
        )

        print(
            f"Usable 10D returns : {usable_10d}"
        )

        print(
            f"Usable 20D returns : {usable_20d}"
        )

        print("=" * 70)

    finally:

        conn.close()


if __name__ == "__main__":

    calculate_forward_returns()