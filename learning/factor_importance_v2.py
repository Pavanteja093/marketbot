import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class FactorImportance:

    def __init__(self):

        self.conn = sqlite3.connect(DB_PATH)

        self.df = pd.read_sql(
            "SELECT * FROM learning_dataset",
            self.conn
        )

        self.df = self.df[
            self.df["return_20d"].notna()
        ].copy()

    def analyze_factor(
        self,
        column,
        bins=5
    ):

        data = self.df.copy()

        data["bucket"] = pd.qcut(
            data[column],
            q=bins,
            duplicates="drop"
        )

        summary = (
            data
            .groupby("bucket", observed=True)
            .agg(
                Trades=("symbol", "count"),
                WinRate=("success_20d", "mean"),
                AvgReturn=("return_20d", "mean"),
                MedianReturn=("return_20d", "median"),
                StdDev=("return_20d", "std"),
                BestReturn=("return_20d", "max"),
                WorstReturn=("return_20d", "min")
            )
            .reset_index()
        )

        summary["WinRate"] *= 100

        summary = summary.round(2)

        return summary

    def save_report(
        self,
        factor,
        summary
    ):

        filename = (
            BASE_DIR /
            "learning" /
            f"{factor}_importance.csv"
        )

        summary.to_csv(
            filename,
            index=False
        )

    def close(self):

        self.conn.close()


def demo():

    engine = FactorImportance()

    factors = [

        "intelligence_score",

        "total_score",

        "sector_strength",

        "position_pct",

        "change_pct"

    ]

    for factor in factors:

        print("\n")

        print("=" * 60)

        print(factor.upper())

        print("=" * 60)

        report = engine.analyze_factor(factor)

        print(report.to_string(index=False))

        engine.save_report(
            factor,
            report
        )

    engine.close()


if __name__ == "__main__":

    demo()