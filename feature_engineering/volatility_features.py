"""
MarketBot Feature Engineering

Volatility Features
"""

import numpy as np
import pandas as pd

from feature_engineering.base_feature import BaseFeatureModule

from feature_engineering.utils import (
    atr,
    true_range,
    historical_volatility,
    rolling_mean,
)


class VolatilityFeatures(BaseFeatureModule):

    NAME = "Volatility Features"

    VERSION = "1.0.0"

    DESCRIPTION = "Generates volatility-based market features."

    MIN_HISTORY = 20

    FEATURES = [

        "true_range",

        "atr_14",

        "rolling_std_20",

        "historical_volatility",

        "volatility_ratio",

        "volatility_expansion",

        "volatility_regime",

    ]

    FEATURE_COUNT = len(FEATURES)

    def generate(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        df = df.copy()

        if not self.validate_history(df):

            return self.initialize_features(df)

        # ----------------------------------
        # True Range
        # ----------------------------------

        previous_close = df["close"].shift(1)

        df["true_range"] = true_range(

            df["high"],

            df["low"],

            previous_close,

        )

        # ----------------------------------
        # ATR
        # ----------------------------------

        df["atr_14"] = atr(df)

        # ----------------------------------
        # Rolling Standard Deviation
        # ----------------------------------

        df["rolling_std_20"] = (

            df["close"]

            .rolling(20)

            .std()

        )

        # ----------------------------------
        # Historical Volatility
        # ----------------------------------

        df["historical_volatility"] = (

            historical_volatility(

                df["close"],

                20,

            )

        )

        # ----------------------------------
        # ATR Relative to Price
        # ----------------------------------

        df["volatility_ratio"] = (

            df["atr_14"]

            / df["close"]

        ) * 100

        # ----------------------------------
        # Volatility Expansion
        # ----------------------------------

        atr_average = rolling_mean(

            df["atr_14"],

            20,

        )

        df["volatility_expansion"] = (

            df["atr_14"]

            / atr_average

        )

        # ----------------------------------
        # Regime Classification
        # ----------------------------------

        df["volatility_regime"] = "Normal"

        df.loc[

            df["volatility_expansion"] > 1.20,

            "volatility_regime",

        ] = "High"

        df.loc[

            df["volatility_expansion"] < 0.80,

            "volatility_regime",

        ] = "Low"

        return df