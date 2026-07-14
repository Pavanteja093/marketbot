import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"


class ResearchValidator:

    def __init__(self):
        pass

    def load_research_data(self):
        
        conn = sqlite3.connect(str(DB_PATH))

        query = """
        SELECT *
        FROM trend_day_research
        ORDER BY trade_date
        """

        df = pd.read_sql(query, conn)

        conn.close()

        return df

    def record_count(self, df):
        
        print("\nRECORD COUNT")
        print("-" * 40)

        print(f"Research Records : {len(df)}")

    def missing_values(self, df):
        
        print("\nMISSING VALUES")
        print("-" * 40)

        missing = df.isnull().sum()

        print(missing)

    def duplicate_records(self, df):
        
        print("\nDUPLICATE RECORDS")
        print("-" * 40)

        duplicates = df.duplicated().sum()

        print(f"Duplicates : {duplicates}")

    def outlier_check(self, df):
        
        print("\nOUTLIER CHECK")
        print("-" * 40)

        trend_outliers = len(
            df[df["trendiness_score"] > 1]
        )

        efficiency_outliers = len(
            df[df["efficiency_ratio"] > 1]
        )

        atr_outliers = len(
            df[df["atr_multiple"] < 0]
        )

        print(f"Trendiness > 1 : {trend_outliers}")
        print(f"Efficiency > 1 : {efficiency_outliers}")
        print(f"ATR < 0        : {atr_outliers}")

    def latest_research_date(self, df):
        
        print("\nLATEST RESEARCH")
        print("-" * 40)

        if len(df) == 0:

            print("No research records.")

            return

        latest = df["trade_date"].max()

        print(f"Latest Date : {latest}")

    def run(self):

        print("\n" + "=" * 60)
        print("RESEARCH VALIDATOR")
        print("=" * 60)

        df = self.load_research_data()

        self.record_count(df)
        self.missing_values(df)
        self.duplicate_records(df)
        self.outlier_check(df)
        self.latest_research_date(df)


if __name__ == "__main__":

    engine = ResearchValidator()

    engine.run()