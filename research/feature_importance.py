import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

class FeatureImportance:

    def __init__(self):
        self.results = {}
        self.verbose = True

    def load_data(self):
        conn = sqlite3.connect(str(DB_PATH))

        df = pd.read_sql(
            "SELECT * FROM trend_day_research",
            conn
        )

        conn.close()

        self.results["sample_size"] = len(df)

        return df

    def rank_features(self, df):

        features = [
            "efficiency_ratio",
            "atr_multiple",
            "gap_percent"
        ]

        importance = []

        target = "trendiness_score"

        for feature in features:

            # Skip features that are completely empty
            if df[feature].notna().sum() == 0:
                correlation = 0
                completeness = 0
            else:
                correlation = abs(
                    df[[feature, target]]
                    .corr()
                    .loc[feature, target]
                )

                if pd.isna(correlation):
                    correlation = 0

                completeness = (
                    df[feature].notna().mean()
                )

            importance_score = (
                correlation * 70
                +
                completeness * 30
            )

            importance.append({

                "feature": feature,

                "correlation": correlation,

                "completeness": completeness,

                "importance_score": importance_score

            })

        importance = pd.DataFrame(importance)

        importance = importance.sort_values(
            by="importance_score",
            ascending=False
        )

        self.results["importance"] = importance

        return importance

    def print_rankings(self, importance):

        print("\nFEATURE IMPORTANCE")
        print("-" * 60)

        print(
            importance[
                [
                    "feature",
                    "correlation",
                    "completeness",
                    "importance_score"
                ]
            ]
        )

        print("\nRECOMMENDATIONS")
        print("-" * 60)

        for _, row in importance.iterrows():

            if row["importance_score"] >= 70:

                recommendation = "Increase feature weight"

            elif row["importance_score"] >= 40:

                recommendation = "Monitor"

            else:

                recommendation = "Need more data"

            print(
                f"{row['feature']:<20}"
                f"{row['importance_score']:>8.2f}"
                f"   {recommendation}"
            )

    def run(self, verbose=True):

        self.verbose = verbose

        print("\n" + "=" * 60)
        print("FEATURE IMPORTANCE")
        print("=" * 60)

        df = self.load_data()

        print(f"\nTrend Research Records : {len(df)}")

        importance = self.rank_features(df)

        self.print_rankings(importance)

        return self.results

if __name__ == "__main__":

    engine = FeatureImportance()

    engine.run()