import pandas as pd

from research.correlation_engine import CorrelationEngine
from research.feature_importance import FeatureImportance


class ResearchReport:

    def __init__(self):

        self.correlation = CorrelationEngine()

        self.feature_importance = FeatureImportance()

    def run(self):

        print("\n" + "=" * 60)
        print("RESEARCH REPORT")
        print("=" * 60)

        corr = self.correlation.run(verbose=False)

        features = self.feature_importance.run(verbose=False)

        print("\n" + "=" * 60)
        print("RESEARCH SUMMARY")
        print("=" * 60)

        print(f"Research Records : {corr['sample_size']}")

        if corr["warning"]:
            print(corr["warning"])

        print()

        print("Top Features")

        print(
            features["importance"][
                [
                    "feature",
                    "importance_score"
                ]
            ]
        )


if __name__ == "__main__":

    report = ResearchReport()

    report.run()