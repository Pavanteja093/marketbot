"""
MarketBot Feature Registry
"""

from feature_engineering.price_features import PriceFeatures


FEATURE_REGISTRY = {
    "price": PriceFeatures(),
}