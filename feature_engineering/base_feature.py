"""
MarketBot Feature Engineering

Base Feature Module
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd


class BaseFeatureModule(ABC):
    """
    Base class for all feature modules.
    """

    NAME = "Base Module"
    VERSION = "1.0.0"
    DESCRIPTION = ""

    MIN_HISTORY = 1

    FEATURES = []

    @abstractmethod
    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate engineered features.
        """
        raise NotImplementedError

    def validate_history(self, df) -> bool:
        return len(df) >= self.MIN_HISTORY

    def initialize_features(self, df: pd.DataFrame) -> pd.DataFrame:

        for feature in self.FEATURES:
            df[feature] = np.nan

        return df