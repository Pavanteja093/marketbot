import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class LearningSummary:

    def __init__(self):

        self.conn = sqlite3.connect(DB_PATH)

        self.df = pd.read_sql(
            "SELECT * FROM learning_dataset",
            self.conn
        )

        self.df = self.df[
            self.df["return_20d"].notna()
        ].copy()

    def dataset_summary(self):

        return {

            "Rows": len(self.df),

            "Trading Days":
                self.df["trade_date"].nunique(),

            "Stocks":
                self.df["symbol"].nunique()

        }

    def model_summary(self):

        return {

            "Average Return":
                round(
                    float(
                        self.df["return_20d"].mean()
                    ),
                    2
                ),

            "Median Return":
                round(
                    float(
                        self.df["return_20d"].median()
                    ),
                    2
                ),

            "Win Rate":
                round(
                    float(
                        self.df["success_20d"].mean()
                    ) * 100,
                    2
                ),

            "Best Return":
                round(
                    float(
                        self.df["return_20d"].max()
                    ),
                    2
                ),

            "Worst Return":
                round(
                    float(
                        self.df["return_20d"].min()
                    ),
                    2
                )

        }

    def grade_summary(self):

        return (
            self.df
            .groupby("grade", observed=True)
            .agg(

                Trades=("symbol", "count"),

                WinRate=("success_20d", "mean"),

                AvgReturn=("return_20d", "mean")

            )
            .round(2)
        )

    def sector_summary(self):

        return (
            self.df
            .groupby("sector", observed=True)
            .agg(

                Trades=("symbol", "count"),

                WinRate=("success_20d", "mean"),

                AvgReturn=("return_20d", "mean")

            )
            .round(2)
            .sort_values(
                "AvgReturn",
                ascending=False
            )
        )

    def best_setup(self):

        top = self.df.nlargest(
            100,
            "return_20d"
        )

        return {

            "Average Intelligence Score":
                round(
                    float(
                        top["intelligence_score"].mean()
                    ),
                    2
                ),

            "Average Sector Strength":
                round(
                    float(
                        top["sector_strength"].mean()
                    ),
                    2
                ),

            "Average Position %":
                round(
                    float(
                        top["position_pct"].mean()
                    ),
                    2
                )

        }

    def recommendations(self):

        return [

            "Continue collecting historical data.",

            "Increase feature engineering.",

            "Add ATR, RSI, ADX and VWAP.",

            "Introduce Market Regime Detection.",

            "Build Random Forest model.",

            "Build XGBoost model."

        ]

    def export_csv(self):

        self.grade_summary().to_csv(
            BASE_DIR /
            "learning" /
            "grade_summary.csv"
        )

        self.sector_summary().to_csv(
            BASE_DIR /
            "learning" /
            "sector_summary.csv"
        )

    def close(self):

        self.conn.close()


def demo():

    summary = LearningSummary()

    print("\n")
    print("=" * 60)
    print("MARKETBOT LEARNING REPORT")
    print("=" * 60)

    print("\nDATASET")
    print(summary.dataset_summary())

    print("\nMODEL")
    print(summary.model_summary())

    print("\nGRADE PERFORMANCE")
    print(summary.grade_summary())

    print("\nSECTOR PERFORMANCE")
    print(summary.sector_summary())

    print("\nBEST HISTORICAL SETUP")
    print(summary.best_setup())

    print("\nRECOMMENDATIONS")

    for item in summary.recommendations():

        print("-", item)

    summary.export_csv()

    summary.close()


if __name__ == "__main__":

    demo()