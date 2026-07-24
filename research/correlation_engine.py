import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class CorrelationEngine:

    def __init__(self):
        self.results = {}
        self.verbose = True

    def load_research_data(self):
        
        conn = sqlite3.connect(str(DB_PATH))

        df = pd.read_sql(
            "SELECT * FROM trend_day_research",
            conn
        )

        conn.close()

        self.results["sample_size"] = len(df)
        return df
    
    def validate_data(self, df):

        print("\nVALIDATING RESEARCH DATA")
        print("-" * 40)

        sample_size = len(df)

        if sample_size < 30:
            warning = (
                f"WARNING: Only {sample_size} observations. "
                "Correlation statistics are unreliable."
            )
        else:
            warning = None

        self.results["warning"] = warning

        if warning:
            print(warning)

    def correlation_matrix(self, df):

        print("\nCORRELATION ANALYSIS")
        print("-" * 40)

        columns = [
            "trendiness_score",
            "efficiency_ratio",
            "atr_multiple"
        ]

        pearson = df[columns].corr(method="pearson")
        spearman = df[columns].corr(method="spearman")
        kendall = df[columns].corr(method="kendall")

        self.results["pearson"] = pearson
        self.results["spearman"] = spearman
        self.results["kendall"] = kendall

        print("\nPearson")
        print(pearson.round(3))

        print("\nSpearman")
        print(spearman.round(3))

        print("\nKendall")
        print(kendall.round(3))

        return pearson

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

    def recommendations(self):

        print("\nRESEARCH RECOMMENDATIONS")
        print("-" * 40)

        pearson = self.results["pearson"]

        pairs = []

        for i in pearson.columns:
            for j in pearson.columns:

                if i >= j:
                    continue

                pairs.append((i, j, abs(pearson.loc[i, j])))

        pairs.sort(key=lambda x: x[2], reverse=True)

        best = pairs[0]

        print(f"Sample Size            : {self.results['sample_size']}")

        if self.results["warning"]:
            print(self.results["warning"])

        print(f"\nStrongest Relationship : {best[0]} ↔ {best[1]}")
        print(f"Correlation            : {best[2]:.3f}")

        if best[2] >= 0.70:
            print("Recommendation         : Strong predictive candidate")
        elif best[2] >= 0.40:
            print("Recommendation         : Moderate predictive signal")
        else:
            print("Recommendation         : Weak relationship")

        print("\nNext Actions")
        print("------------")

        if self.results["sample_size"] < 30:
            print("• Collect more historical data.")
            print("• Do NOT use these correlations for feature weighting yet.")
        else:
            print("• Safe to begin feature weighting research.")
    
    def run(self, verbose=True):

        self.verbose = verbose

        print("\n" + "=" * 60)
        if verbose:
            print("CORRELATION ENGINE")
        print("=" * 60)

        df = self.load_research_data()

        self.validate_data(df)

        corr = self.correlation_matrix(df)

        self.strongest_positive(corr)

        self.strongest_negative(corr)

        self.recommendations()

        return self.results


if __name__ == "__main__":

    engine = CorrelationEngine()

    engine.run()