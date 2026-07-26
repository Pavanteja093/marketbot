"""
MarketBot Feature Engineering

Trend Features Module
"""

import numpy as np
import pandas as pd

from feature_engineering.base_feature import BaseFeatureModule
from feature_engineering.utils import ema, sma

class TrendFeatures(BaseFeatureModule):
    """
    Generate trend-based engineered features.
    """

    NAME = "Trend Features"
    VERSION = "1.0.0"
    DESCRIPTION = "Generates trend-based market features."

    MIN_HISTORY = 50

    FEATURES = [
        "ema_20",
        "ema_50",
        "sma_20",
        "sma_50",
        "trend_direction",
        "trend_strength",
    ]

    FEATURE_COUNT = len(FEATURES)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:

        df = df.copy()

        # --------------------------------------------------
        # Not enough history
        # --------------------------------------------------

        if not self.validate_history(df):

            return self.initialize_features(df)

        # --------------------------------------------------
        # Moving Averages
        # --------------------------------------------------

        df["ema_20"] = ema(df["close"], 20)

        df["ema_50"] = ema(df["close"], 50)

        df["sma_20"] = sma(df["close"], 20)

        df["sma_50"] = sma(df["close"], 50)

        # --------------------------------------------------
        # Trend Direction
        # --------------------------------------------------

        df["trend_direction"] = np.where(
            df["ema_20"] > df["ema_50"],
            "Bullish",
            "Bearish",
        )

        # --------------------------------------------------
        # Trend Strength
        # --------------------------------------------------

        distance = (
            abs(df["ema_20"] - df["ema_50"])
            / df["close"]
        ) * 100

        df["trend_strength"] = distance.round(2)

        return df