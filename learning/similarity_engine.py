import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class SimilarityEngine:

    def __init__(self):

        self.conn = sqlite3.connect(DB_PATH)

        self.df = pd.read_sql(
            "SELECT * FROM learning_dataset",
            self.conn
        )

    def similar_market(
        self,
        intelligence_score,
        sector_strength,
        position_pct,
        tolerance=5
    ):

        data = self.df.copy()

        data = data[
            data["return_20d"].notna()
        ]

        data = data[
            (
                data["intelligence_score"]
                .between(
                    intelligence_score - tolerance,
                    intelligence_score + tolerance
                )
            )
            &
            (
                data["sector_strength"]
                .between(
                    sector_strength - tolerance,
                    sector_strength + tolerance
                )
            )
            &
            (
                data["position_pct"]
                .between(
                    position_pct - tolerance,
                    position_pct + tolerance
                )
            )
        ]

        return data

    def statistics(self, data):

        if data.empty:

            return None

        data.to_csv(
            BASE_DIR / "learning" / "last_similarity_search.csv",
            index=False
        )

        return {

            "observations": len(data),

            "median_return":
                round(
                    float(data["return_20d"].median()),
                    2
                ),

            "volatility":
                round(
                    float(data["return_20d"].std()),
                    2
                ),

            "average_return":
                round(
                    float(data["return_20d"].mean()),
                    2
                ),

            "win_rate":
                round(
                    float(data["success_20d"].mean() * 100),
                    2
                ),

            "best_return":
                round(
                    float(data["return_20d"].max()),
                    2
                ),

            "worst_return":
                round(
                    float(data["return_20d"].min()),
                    2
                )

        }

    def close(self):

        self.conn.close()


def demo():

    engine = SimilarityEngine()

    sample = engine.similar_market(
        intelligence_score=80,
        sector_strength=2,
        position_pct=80
    )

    stats = engine.statistics(sample)

    print("\n==============================")
    print("SIMILAR MARKET ENGINE")
    print("==============================")

    print(stats)

    engine.close()


if __name__ == "__main__":

    demo()