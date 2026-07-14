import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

class LearningEngine:

    def __init__(self):
        pass
    
    def load_learning_history(self):
        conn = sqlite3.connect(str(DB_PATH))

        df = pd.read_sql(
            "SELECT * FROM learning_history",
            conn
        )

        conn.close()

        return df

    def overall_accuracy(self, df):
        total = len(df)

        correct = df["correct"].sum()

        incorrect = total - correct

        accuracy = (correct / total) * 100 if total else 0

        print("\nOVERALL ACCURACY")
        print("-" * 40)

        print(f"Total Predictions : {total}")
        print(f"Correct           : {correct}")
        print(f"Incorrect         : {incorrect}")
        print(f"Accuracy          : {accuracy:.2f}%")

    def prediction_accuracy(self, df):
        print("\nPREDICTION ACCURACY")
        print("-" * 40)

        for prediction in ["BULLISH", "BEARISH", "NEUTRAL"]:

            subset = df[df["prediction"] == prediction]

            total = len(subset)

            correct = subset["correct"].sum()

            accuracy = (correct / total) * 100 if total else 0

            print(f"{prediction:<10}: {accuracy:.2f}% ({correct}/{total})")

    def strategy_accuracy(self, df):
        print("\nSTRATEGY ACCURACY")
        print("-" * 40)

        strategies = df["strategy"].dropna().unique()

        for strategy in strategies:

            subset = df[df["strategy"] == strategy]

            total = len(subset)

            correct = subset["correct"].sum()

            accuracy = (correct / total) * 100 if total else 0

            print(f"{strategy:<20}: {accuracy:.2f}% ({correct}/{total})")

    def confidence_analysis(self, df):
        print("\nCONFIDENCE ANALYSIS")
        print("-" * 40)

        bands = [

            ("High", df[df["confidence"] >= 80]),

            ("Medium", df[(df["confidence"] >= 60) & (df["confidence"] < 80)]),

            ("Low", df[df["confidence"] < 60])

        ]

        for label, subset in bands:

            total = len(subset)

            correct = subset["correct"].sum()

            accuracy = (correct / total) * 100 if total else 0

            print(f"{label:<10}: {accuracy:.2f}% ({correct}/{total})")

    def improvement_recommendations(self, df):
        print("\nIMPROVEMENT RECOMMENDATIONS")
        print("-" * 40)

        accuracy = (df["correct"].sum() / len(df)) * 100 if len(df) else 0

        if accuracy < 60:

            print("- Improve prediction logic.")

            print("- Review market factors.")

        elif accuracy < 75:

            print("- Fine tune feature weights.")

            print("- Continue collecting learning data.")

        else:

            print("- Model performing well.")

            print("- Continue monitoring.")

    def run(self):
        print("\n" + "=" * 60)
        print("LEARNING ENGINE")
        print("=" * 60)

        df = self.load_learning_history()
        
        print(f"\nLearning Records : {len(df)}")

        self.overall_accuracy(df)

        self.prediction_accuracy(df)

        self.strategy_accuracy(df)

        self.confidence_analysis(df)

        self.improvement_recommendations(df)

        