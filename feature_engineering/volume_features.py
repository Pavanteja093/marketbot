"""
MarketBot Feature Engineering

Volume Features Module
"""

import pandas as pd

from feature_engineering.base_feature import BaseFeatureModule
from feature_engineering.utils import (
    rolling_mean,
    relative_volume,
    volume_ratio,
    volume_change,
    zscore,
)


class VolumeFeatures(BaseFeatureModule):

    NAME = "Volume Features"
    VERSION = "1.0.0"
    DESCRIPTION = "Generates volume-based market features."

    MIN_HISTORY = 20

    FEATURES = [
        "volume_sma20",
        "relative_volume",
        "volume_ratio",
        "volume_change_pct",
        "high_volume",
        "low_volume",
        "volume_zscore",
    ]

    FEATURE_COUNT = len(FEATURES)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:

        df = df.copy()

        if not self.validate_history(df):
            return self.initialize_features(df)

        df["volume_sma20"] = rolling_mean(df["volume"], 20)

        df["relative_volume"] = relative_volume(
            df["volume"],
            20,
        )

        df["volume_ratio"] = volume_ratio(df["volume"])

        df["volume_change_pct"] = volume_change(df["volume"])

        df["volume_zscore"] = zscore(df["volume"], 20)

        df["high_volume"] = df["relative_volume"] > 1.5

        df["low_volume"] = df["relative_volume"] < 0.5


        return df