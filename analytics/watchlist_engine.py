import pandas as pd


class WatchlistEngine:

    def __init__(self, rankings):
        self.rankings = rankings

    def top_overall(self, n=10):
        return self.rankings.nsmallest(n, "overall_rank")

    def top_momentum(self, n=10):
        return self.rankings.nsmallest(n, "momentum_rank")

    def top_trend(self, n=10):
        return self.rankings.nsmallest(n, "trend_rank")

    def top_relative_strength(self, n=10):
        return self.rankings.nsmallest(n, "rs_rank")

    def top_liquidity(self, n=10):
        return self.rankings.nsmallest(n, "liquidity_rank")