import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

class CalibrationEngine:

    def __init__(self):
        pass

    def load_predictions(self):
        conn = sqlite3.connect(str(DB_PATH))

        df = pd.read_sql(
            "SELECT * FROM learning_history",
            conn
        )

        conn.close()

        return df

    def confidence_accuracy(self):
        pass

    def calibration_score(self):
        pass

    def run(self):
        print("\n" + "=" * 60)
        print("CALIBRATION ENGINE")
        print("=" * 60)

        df = self.load_predictions()

        print(f"\nLearning Records : {len(df)}")