"""
MarketBot Feature Engineering

Price Features Module

Transforms raw OHLC price data into standardized
price-derived market features.
"""

import numpy as np
import pandas as pd


class PriceFeatures:
    """
    Generate engineered features derived solely from OHLC price data.
    """

    NAME = "Price Features"

    VERSION = "1.0.0"

    DESCRIPTION = (
        "Generates standardized price-based market features."
    )

    FEATURE_COUNT = 9

    FEATURES = [
        "previous_close",
        "daily_return_pct",
        "intraday_return_pct",
        "high_low_range_pct",
        "body_size_pct",
        "upper_wick_pct",
        "lower_wick_pct",
        "gap_pct",
        "close_position",
    ]

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate price-derived features.

        Parameters
        ----------
        df : pandas.DataFrame

        Returns
        -------
        pandas.DataFrame
        """

        df = df.copy()

        # ----------------------------------
        # Previous Close
        # ----------------------------------

        df["previous_close"] = df["close"].shift(1)

        # ----------------------------------
        # Daily Return (%)
        # ----------------------------------

        df["daily_return_pct"] = (
            (df["close"] - df["previous_close"])
            / df["previous_close"]
        ) * 100

        # ----------------------------------
        # Intraday Return (%)
        # ----------------------------------

        df["intraday_return_pct"] = (
            (df["close"] - df["open"])
            / df["open"]
        ) * 100

        # ----------------------------------
        # Daily Range (%)
        # ----------------------------------

        df["high_low_range_pct"] = (
            (df["high"] - df["low"])
            / df["open"]
        ) * 100

        # ----------------------------------
        # Candle Body (%)
        # ----------------------------------

        df["body_size_pct"] = (
            abs(df["close"] - df["open"])
            / df["open"]
        ) * 100

        # ----------------------------------
        # Upper Wick (%)
        # ----------------------------------

        df["upper_wick_pct"] = (
            (
                df["high"]
                - np.maximum(df["open"], df["close"])
            )
            / df["open"]
        ) * 100

        # ----------------------------------
        # Lower Wick (%)
        # ----------------------------------

        df["lower_wick_pct"] = (
            (
                np.minimum(df["open"], df["close"])
                - df["low"]
            )
            / df["open"]
        ) * 100

        # ----------------------------------
        # Gap (%)
        # ----------------------------------

        df["gap_pct"] = (
            (df["open"] - df["previous_close"])
            / df["previous_close"]
        ) * 100

        # ----------------------------------
        # Close Position (0 → 1)
        # ----------------------------------

        daily_range = df["high"] - df["low"]

        df["close_position"] = np.where(
            daily_range == 0,
            0.5,
            (df["close"] - df["low"]) / daily_range,
        )

        return df