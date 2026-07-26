"""
MarketBot Feature Pipeline
"""

import time

from feature_engineering.feature_registry import FEATURE_REGISTRY


class FeaturePipeline:

    def __init__(self):
        self.registry = FEATURE_REGISTRY

    def run(self, df):

        start = time.perf_counter()

        summary = []

        result = df.copy()

        for module_name, module in self.registry.items():

            before = len(result.columns)

            rows = len(result)

            result = module.generate(result)

            after = len(result.columns)

            summary.append({

                "Module": module.NAME,

                "Version": module.VERSION,

                "Rows": rows,

                "Features": after - before,

                "Status": "OK",

            })

        elapsed = time.perf_counter() - start

        print("\n")
        print("=" * 78)
        print("                 FEATURE ENGINEERING PIPELINE")
        print("=" * 78)

        print(
            f"{'#':<4}"
            f"{'Module':<24}"
            f"{'Version':<10}"
            f"{'Rows':<8}"
            f"{'Features':<10}"
            f"{'Status'}"
        )

        print("-" * 78)

        for index, item in enumerate(summary, start=1):

            print(
                f"{index:<4}"
                f"{item['Module']:<24}"
                f"{item['Version']:<10}"
                f"{item['Rows']:<8}"
                f"{item['Features']:<10}"
                f"{item['Status']}"
            )

        print("-" * 78)

        print(f"Modules Executed : {len(summary)}")
        print(f"Pipeline Time    : {elapsed:.3f} sec")

        print("=" * 78)

        return result