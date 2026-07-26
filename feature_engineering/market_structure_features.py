"""
MarketBot Feature Engineering

Market Structure Features
"""

import pandas as pd

from feature_engineering.base_feature import BaseFeatureModule


class MarketStructureFeatures(BaseFeatureModule):

    NAME = "Market Structure"

    VERSION = "1.0.0"

    DESCRIPTION = (
        "Generates high-level market structure features."
    )

    MIN_HISTORY = 20

    FEATURES = [

        "market_regime",

        "trend_quality",

        "breakout_strength",

        "risk_environment",

    ]

    FEATURE_COUNT = len(FEATURES)

    def generate(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        df = df.copy()

        if not self.validate_history(df):

            return self.initialize_features(df)

        # ------------------------------------
        # Market Regime
        # ------------------------------------

        df["market_regime"] = "Sideways"

        bullish = (
            (df["trend_direction"] == "Bullish")
            &
            (df["momentum_20"] > 0)
        )

        bearish = (
            (df["trend_direction"] == "Bearish")
            &
            (df["momentum_20"] < 0)
        )

        df.loc[bullish, "market_regime"] = "Bull Trend"

        df.loc[bearish, "market_regime"] = "Bear Trend"

        # ------------------------------------
        # Trend Quality
        # ------------------------------------

        df["trend_quality"] = "Weak"

        strong = (
            (df["trend_strength"] > 2)
            &
            (df["relative_volume"] > 1)
        )

        df.loc[strong, "trend_quality"] = "Strong"

        # ------------------------------------
        # Breakout Strength
        # ------------------------------------

        df["breakout_strength"] = (

            df["relative_volume"]

            *

            df["volatility_expansion"]

        )

        # ------------------------------------
        # Risk Environment
        # ------------------------------------

        df["risk_environment"] = "Normal"

        df.loc[
            df["volatility_regime"] == "High",
            "risk_environment",
        ] = "High Risk"

        df.loc[
            df["volatility_regime"] == "Low",
            "risk_environment",
        ] = "Low Risk"

        return df