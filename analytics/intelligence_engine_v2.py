from analytics.feature_engine import FeatureEngine


class IntelligenceEngine:

    def __init__(self):
        self.engine = FeatureEngine()

    def score_stock(
        self,
        history_df,
        market_return=0
    ):

        stock_return = history_df.iloc[-1]["change_pct"]

        features = self.engine.build_features(
            history_df,
            stock_return,
            market_return
        )

        intelligence_score = (
            features["relative_strength"] * 0.25 +
            features["momentum_score"] * 0.20 +
            features["trend_score"] * 0.20 +
            features["volatility_score"] * 0.15 +
            features["liquidity_score"] * 0.20
        )

        features["intelligence_score"] = round(
            intelligence_score,
            2
        )

        return features