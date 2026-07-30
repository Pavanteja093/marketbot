import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class RelativeStrength:

    def __init__(self):

        self.conn = sqlite3.connect(DB_PATH)

    # =====================================================
    # LOAD DATA
    # =====================================================

    def load_market_return(self):

        query = """
        SELECT
            trade_date,
            change_pct

        FROM indices_daily

        WHERE index_name='NIFTY50'

        ORDER BY trade_date DESC

        LIMIT 1
        """

        df = pd.read_sql(query, self.conn)

        if df.empty:
            raise Exception("No NIFTY50 data found.")

        return df.iloc[0]

    def load_factor_history(self, trade_date):

        query = """

        SELECT *

        FROM factor_history

        WHERE trade_date=?

        """

        return pd.read_sql(
            query,
            self.conn,
            params=(trade_date,)
        )

    # =====================================================
    # RELATIVE STRENGTH
    # =====================================================

    def calculate_relative_strength(self, df, market_return):

        df = df.copy()

        df["relative_strength"] = (
            df["change_pct"] -
            market_return
        )

        df["relative_strength"] = (
            df["relative_strength"]
            .round(2)
        )

        df["rs_grade"] = df["relative_strength"].apply(
            self.grade_rs
        )

        return df

    # =====================================================
    # RS GRADE
    # =====================================================

    def grade_rs(self, rs):

        if rs >= 3:
            return "ELITE"

        elif rs >= 2:
            return "VERY_STRONG"

        elif rs >= 1:
            return "STRONG"

        elif rs >= 0:
            return "POSITIVE"

        elif rs >= -1:
            return "NEGATIVE"

        elif rs >= -2:
            return "WEAK"

        else:
            return "VERY_WEAK"

    # =====================================================
    # DATABASE UPDATE
    # =====================================================

    def save(self, df):

        cursor = self.conn.cursor()

        for _, row in df.iterrows():

            cursor.execute(
                """
                UPDATE factor_history

                SET

                    relative_strength=?,

                    rs_grade=?

                WHERE

                    trade_date=?

                AND

                    symbol=?

                """,

                (

                    float(row["relative_strength"]),

                    row["rs_grade"],

                    row["trade_date"],

                    row["symbol"]

                )

            )

        self.conn.commit()

    # =====================================================
    # REPORT
    # =====================================================

    def report(self, df, market_return):

        strongest = (
            df.sort_values(
                "relative_strength",
                ascending=False
            )
            .head(5)
        )

        weakest = (
            df.sort_values(
                "relative_strength"
            )
            .head(5)
        )

        print("\n")
        print("=" * 65)
        print("          MARKETBOT RELATIVE STRENGTH V1")
        print("=" * 65)

        print(
            f"Trade Date     : {df.iloc[0]['trade_date']}"
        )

        print(
            f"NIFTY Return   : {market_return:.2f}%"
        )

        print(
            f"Stocks Updated : {len(df)}"
        )

        print()

        print("Top 5 Strongest")

        print("-" * 65)

        for _, row in strongest.iterrows():

            print(
                f"{row['symbol']:<15}"
                f"{row['relative_strength']:>8.2f}"
                f"   {row['rs_grade']}"
            )

        print()

        print("Top 5 Weakest")

        print("-" * 65)

        for _, row in weakest.iterrows():

            print(
                f"{row['symbol']:<15}"
                f"{row['relative_strength']:>8.2f}"
                f"   {row['rs_grade']}"
            )

    # =====================================================
    # RUN
    # =====================================================

    def run(self):

        try:

            market = self.load_market_return()

            trade_date = market["trade_date"]

            market_return = float(market["change_pct"])

            df = self.load_factor_history(trade_date)

            if df.empty:

                print("\nNo factor_history records found.")
                print(f"Trade Date : {trade_date}")
                return

            df = self.calculate_relative_strength(
                df,
                market_return
            )

            self.save(df)

            self.report(
                df,
                market_return
            )

            print("\n")
            print("=" * 65)
            print("Relative Strength calculation completed successfully.")
            print("=" * 65)

        except Exception as e:

            print("\n")
            print("=" * 65)
            print("RELATIVE STRENGTH FAILED")
            print("=" * 65)
            print(e)

            raise

        finally:

            self.conn.close()


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    RelativeStrength().run()