"""
Feature Store
"""


class FeatureStore:

    def __init__(self):
        self._data = None

    def save(self, dataframe):

        self._data = dataframe.copy()

    def load(self):

        return self._data