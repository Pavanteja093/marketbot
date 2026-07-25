"""
MarketBot Feature Pipeline
"""

from feature_engineering.feature_registry import FEATURE_REGISTRY


class FeaturePipeline:

    def __init__(self):
        self.registry = FEATURE_REGISTRY

    def run(self, df):

        result = df.copy()

        print("\n===================================")
        print(" FEATURE ENGINEERING PIPELINE")
        print("===================================\n")

        for module_name, module in self.registry.items():

            print(f"Running Module : {module.NAME}")
            print(f"Version        : {module.VERSION}")

            before = len(result.columns)

            result = module.generate(result)

            after = len(result.columns)

            print(f"Features Added : {after - before}")
            print("-------------------------------")

        print("\nPipeline Complete.\n")

        return result