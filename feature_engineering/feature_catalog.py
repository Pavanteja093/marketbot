"""
MarketBot Feature Catalog
"""

from feature_engineering.feature_registry import FEATURE_REGISTRY


class FeatureCatalog:

    def __init__(self):

        self.catalog = {}

        self.build()

    def build(self):

        for module in FEATURE_REGISTRY.values():

            category = module.NAME.replace(" Features", "")

            for feature in module.FEATURES:

                self.catalog[feature] = {

                    "module": module.NAME,

                    "category": category,

                    "version": module.VERSION,

                }

    def list_features(self):

        return list(self.catalog.keys())

    def get(self, feature):

        return self.catalog.get(feature)

    def list_by_module(self, module):

        return {

            k: v
            for k, v in self.catalog.items()
            if v["module"] == module
        }