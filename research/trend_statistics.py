import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

class TrendStatistics:

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

    def summary_statistics(self, df):
        
        print("\nSUMMARY STATISTICS")
        print("-" * 40)

        print(f"Research Records      : {len(df)}")

        if len(df) == 0:
            return

        print(f"Average Trendiness    : {df['trendiness_score'].mean():.4f}")
        print(f"Average Efficiency    : {df['efficiency_ratio'].mean():.4f}")
        print(f"Average ATR Multiple  : {df['atr_multiple'].mean():.4f}")

    def distribution(self, df):
        
        if len(df) == 0:
            return

        print("\nDISTRIBUTION")
        print("-" * 40)

        for column in [
            "trendiness_score",
            "efficiency_ratio",
            "atr_multiple"
        ]:

            print(f"\n{column}")

            print(f"Mean   : {df[column].mean():.4f}")
            print(f"Median : {df[column].median():.4f}")
            print(f"Std    : {df[column].std():.4f}")
            print(f"Min    : {df[column].min():.4f}")
            print(f"Max    : {df[column].max():.4f}")

    def top_trend_days(self, df):
        
        if len(df) == 0:
            return

        print("\nTOP TREND DAYS")
        print("-" * 40)

        top = df.sort_values(
            by="trendiness_score",
            ascending=False
        ).head(5)

        print(
            top[
                [
                    "trade_date",
                    "index_name",
                    "trendiness_score",
                    "efficiency_ratio"
                ]
            ]
        )

    def least_trending_days(self, df):
        
        if len(df) == 0:
            return

        print("\nLEAST TRENDING DAYS")
        print("-" * 40)

        bottom = df.sort_values(
            by="trendiness_score"
        ).head(5)

        print(
            bottom[
                [
                    "trade_date",
                    "index_name",
                    "trendiness_score",
                    "efficiency_ratio"
                ]
            ]
        )

    def run(self):

        print("\n" + "=" * 60)
        print("TREND STATISTICS")
        print("=" * 60)

        df = self.load_research_data()

        self.summary_statistics(df)

        self.distribution(df)

        self.top_trend_days(df)

        self.least_trending_days(df)

if __name__ == "__main__":

    TrendStatistics().run()