import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class CorrelationEngine:

    def __init__(self):
        pass

    def load_research_data(self):
        
        conn = sqlite3.connect(str(DB_PATH))

        df = pd.read_sql(
            "SELECT * FROM trend_day_research",
            conn
        )

        conn.close()

        return df

    def correlation_matrix(self, df):
        
        print("\nCORRELATION MATRIX")
        print("-" * 40)

        columns = [
            "trendiness_score",
            "efficiency_ratio",
            "atr_multiple"
        ]

        corr = df[columns].corr()

        print(corr.round(3))

        return corr

    def strongest_positive(self, corr):
        
        print("\nSTRONGEST POSITIVE CORRELATIONS")
        print("-" * 40)

        pairs = []

        for i in corr.columns:
            for j in corr.columns:

                if i >= j:
                    continue

                pairs.append((i, j, corr.loc[i, j]))

        pairs.sort(key=lambda x: x[2], reverse=True)

        for feature1, feature2, value in pairs:

            print(f"{feature1} <-> {feature2} : {value:.3f}")

    def strongest_negative(self, corr):
        
        print("\nNEGATIVE CORRELATIONS")
        print("-" * 40)

        negative = []

        for i in corr.columns:
            for j in corr.columns:

                if i >= j:
                    continue

                value = corr.loc[i, j]

                if value < 0:

                    negative.append((i, j, value))

        if len(negative) == 0:

            print("No negative correlations found.")

        else:

            negative.sort(key=lambda x: x[2])

            for feature1, feature2, value in negative:

                print(f"{feature1} <-> {feature2} : {value:.3f}")

    def recommendations(self, corr):
        
        print("\nRESEARCH RECOMMENDATIONS")
        print("-" * 40)

        pairs = []

        for i in corr.columns:
            for j in corr.columns:

                if i >= j:
                    continue

                pairs.append((i, j, abs(corr.loc[i, j])))

        pairs.sort(key=lambda x: x[2], reverse=True)

        best = pairs[0]

        print(f"Strongest Relationship : {best[0]} ↔ {best[1]}")
        print(f"Correlation            : {best[2]:.3f}")

        if best[2] >= 0.70:

            print("Recommendation         : Strong predictive candidate")

        elif best[2] >= 0.40:

            print("Recommendation         : Moderate relationship")

        else:

            print("Recommendation         : Weak relationship")

    def run(self):

        print("\n" + "=" * 60)
        print("CORRELATION ENGINE")
        print("=" * 60)

        df = self.load_research_data()

        corr = self.correlation_matrix(df)

        self.strongest_positive(corr)

        self.strongest_negative(corr)

        self.recommendations(corr)


if __name__ == "__main__":

    engine = CorrelationEngine()

    engine.run()