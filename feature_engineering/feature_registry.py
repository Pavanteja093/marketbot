"""
MarketBot Feature Registry
"""

from feature_engineering.price_features import PriceFeatures
from feature_engineering.trend_features import TrendFeatures
from feature_engineering.momentum_features import MomentumFeatures
from feature_engineering.volume_features import VolumeFeatures
from feature_engineering.volatility_features import VolatilityFeatures
from feature_engineering.market_structure_features import MarketStructureFeatures

FEATURE_REGISTRY = {

    "price": PriceFeatures(),

    "trend": TrendFeatures(),

    "momentum": MomentumFeatures(),
    
    "volume": VolumeFeatures(),

    "volatility": VolatilityFeatures(),

    "market_structure": MarketStructureFeatures(),

}