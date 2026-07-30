import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class MarketMemory:

    def __init__(self):

        self.conn = sqlite3.connect(DB_PATH)

    def dataset(self):

        return pd.read_sql(
            "SELECT * FROM learning_dataset",
            self.conn
        )

    def top_winners(self, limit=20):

        return pd.read_sql(
            f"""
            SELECT
                trade_date,
                symbol,
                sector,
                intelligence_score,
                return_20d
            FROM learning_dataset
            WHERE return_20d IS NOT NULL
            ORDER BY return_20d DESC
            LIMIT {limit}
            """,
            self.conn
        )

    def top_losers(self, limit=20):

        return pd.read_sql(
            f"""
            SELECT
                trade_date,
                symbol,
                sector,
                intelligence_score,
                return_20d
            FROM learning_dataset
            WHERE return_20d IS NOT NULL
            ORDER BY return_20d ASC
            LIMIT {limit}
            """,
            self.conn
        )

    def grade_summary(self):

        return pd.read_sql(
            """
            SELECT

                grade,

                COUNT(*) AS total,

                AVG(return_20d) AS avg_return,

                AVG(success_20d) * 100 AS win_rate

            FROM learning_dataset

            WHERE return_20d IS NOT NULL

            GROUP BY grade

            ORDER BY avg_return DESC
            """,
            self.conn
        )

    def sector_summary(self):

        return pd.read_sql(
            """
            SELECT

                sector,

                COUNT(*) AS observations,

                AVG(return_20d) AS avg_return,

                AVG(success_20d) * 100 AS win_rate

            FROM learning_dataset

            WHERE return_20d IS NOT NULL

            GROUP BY sector

            ORDER BY avg_return DESC
            """,
            self.conn
        )

    def close(self):

        self.conn.close()


def demo():

    memory = MarketMemory()

    def high_confidence(self, score=80):

        return pd.read_sql(
            f"""
            SELECT *

            FROM learning_dataset

            WHERE intelligence_score >= {score}

            ORDER BY intelligence_score DESC
            """,
            self.conn
        )

    print("\n==============================")
    print("GRADE SUMMARY")
    print("==============================")

    print(memory.grade_summary().to_string(index=False))

    print("\n==============================")
    print("TOP WINNERS")
    print("==============================")

    print(memory.top_winners(10).to_string(index=False))

    print("\n==============================")
    print("SECTOR SUMMARY")
    print("==============================")

    print(memory.sector_summary().to_string(index=False))

    memory.grade_summary().to_csv(
        BASE_DIR / "learning" / "grade_summary.csv",
        index=False
    )

    memory.sector_summary().to_csv(
        BASE_DIR / "learning" / "sector_summary.csv",
        index=False
    )

    memory.close()


if __name__ == "__main__":

    demo()