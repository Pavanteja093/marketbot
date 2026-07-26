"""
MarketBot Feature Engineering

Momentum Features Module
"""

import pandas as pd

from feature_engineering.base_feature import BaseFeatureModule
from feature_engineering.utils import momentum, roc

class MomentumFeatures(BaseFeatureModule):

    NAME = "Momentum Features"
    VERSION = "1.0.0"
    DESCRIPTION = "Generates momentum-based market features."

    MIN_HISTORY = 20

    FEATURES = [
        "momentum_5",
        "momentum_10",
        "momentum_20",
        "roc_5",
        "roc_10",
        "price_above_ema20",
        "price_above_sma20",
    ]

    FEATURE_COUNT = len(FEATURES)

    def generate(self, df: pd.DataFrame):

        df = df.copy()

        if not self.validate_history(df):

            return self.initialize_features(df)

        # -----------------------------------------
        # Percentage Momentum
        # -----------------------------------------

        df["momentum_5"] = momentum(df["close"], 5)
        df["momentum_10"] = momentum(df["close"], 10)
        df["momentum_20"] = momentum(df["close"], 20)

        df["roc_5"] = roc(df["close"], 5)
        df["roc_10"] = roc(df["close"], 10)
        df["momentum_10"] = df["close"].pct_change(10) * 100
        df["momentum_20"] = df["close"].pct_change(20) * 100

        # -----------------------------------------
        # Rate of Change
        # -----------------------------------------

        df["roc_5"] = (
            (df["close"] - df["close"].shift(5))
            / df["close"].shift(5)
        ) * 100

        df["roc_10"] = (
            (df["close"] - df["close"].shift(10))
            / df["close"].shift(10)
        ) * 100

        # -----------------------------------------
        # Position Relative to Trend
        # -----------------------------------------

        df["price_above_ema20"] = (
            df["close"] > df["ema_20"]
        )

        df["price_above_sma20"] = (
            df["close"] > df["sma_20"]
        )

        return df