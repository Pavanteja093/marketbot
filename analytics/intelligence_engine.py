"""
MarketBot Intelligence Engine

Single source of truth for all stock feature engineering.

Pipeline

stocks_daily
      │
      ▼
Relative Strength
Momentum
Sector Strength
Market Regime
Volatility
Trend Strength
Volume Strength
      │
      ▼
Intelligence Score
      │
      ▼
factor_history
"""

from database.db import get_connection

from analytics.relative_strength import (
    calculate_relative_strength
)

from analytics.momentum_score import (
    calculate_momentum
)


class IntelligenceEngine:

    def __init__(self):

        self.conn = get_connection()

        self.cursor = self.conn.cursor()


    def load_market_data(self):

        """
        Load required market data
        """

        pass


    def calculate_features(self):

        """
        Compute every predictive feature
        """

        pass


    def calculate_score(self):

        """
        Intelligence Score
        """

        pass


    def save_factor_history(self):

        """
        Save into factor_history
        """

        pass


    def run(self):

        self.load_market_data()

        self.calculate_features()

        self.calculate_score()

        self.save_factor_history()

        self.conn.close()


def build_intelligence():

    IntelligenceEngine().run()


if __name__ == "__main__":

    build_intelligence()