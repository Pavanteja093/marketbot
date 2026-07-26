"""
Feature Store
"""

import pandas as pd


class FeatureStore:

    def __init__(self):
        self.data = pd.DataFrame()

    def save(self, df):

        self.data = df.copy()

    def load(self):

        return self.data.copy()

    def clear(self):

        self.data = pd.DataFrame()