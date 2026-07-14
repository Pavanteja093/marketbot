import sqlite3
import pandas as pd

from pathlib import Path

from database.research_repository import save_trend_research

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

class TrendDayResearch:

    def __init__(self):
        pass

    def load_market_data(self):
        
        conn = sqlite3.connect(str(DB_PATH))

        query = """
        SELECT *
        FROM indices_daily
        ORDER BY trade_date DESC
        LIMIT 3
        """

        df = pd.read_sql(query, conn)

        conn.close()

        return df

    def calculate_gap_percent(self):

        df = self.load_market_data()

        df["gap_percent"] = (
            (df["open"] - df["previous_close"])
            / df["previous_close"]
        ) * 100

        return df

    def calculate_close_return(self):

        df = self.calculate_gap_percent()

        df["close_return"] = (
            (df["close"] - df["open"])
            / df["open"]
        ) * 100

        return df

    def calculate_trendiness(self):

        df = self.calculate_close_return()

        df["trendiness_score"] = abs(df["close_return"])

        return df

    def calculate_efficiency_ratio(self):

        df = self.calculate_trendiness()

        df["efficiency_ratio"] = (
            abs(df["close"] - df["open"])
            /
            (df["high"] - df["low"])
        )

        return df

    def calculate_atr_multiple(self):
        
        df = self.calculate_efficiency_ratio()

        df["atr_multiple"] = (
            df["high"] - df["low"]
        ) / df["close"]

        return df

    def build_research_record(self):
        
        df = self.calculate_atr_multiple()

        records = []

        for _, row in df.iterrows():

            records.append({

                "trade_date": row["trade_date"],

                "index_name": row["index_name"],

                "gap_percent": row["gap_percent"],

                "close_return": row["close_return"],

                "trendiness_score": row["trendiness_score"],

                "efficiency_ratio": row["efficiency_ratio"],

                "atr_multiple": row["atr_multiple"]

            })

        return records

    def save_research_record(self):
        
        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        records = self.build_research_record()

        for record in records:

            cursor.execute(
                """
                INSERT OR REPLACE INTO trend_day_research
                (
                    trade_date,
                    index_name,

                    trendiness_score,
                    
                    efficiency_ratio,

                    atr_multiple,

                    gap_percent,

                    close_return
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        record["trade_date"],
                        record["index_name"],

                        record["trendiness_score"],

                        record["efficiency_ratio"],

                        record["atr_multiple"],

                        record["gap_percent"],

                        record["close_return"]
                    )

                )
            )

        conn.commit()

        conn.close()

        print(f"\nSaved {len(records)} research records.")

    def process_index(self):
        pass

    def run(self):

        print("\n" + "=" * 60)
        print("TREND DAY RESEARCH")
        print("=" * 60)

        self.save_research_record()

if __name__ == "__main__":

    engine = TrendDayResearch()

    engine.run()