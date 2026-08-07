class ExplanationEngine:

    def explain(self, features):

        reasons = []

        if features["relative_strength"] >= 80:
            reasons.append("Strong Relative Strength")

        if features["trend_score"] >= 80:
            reasons.append("Strong Trend")

        if features["momentum_score"] >= 80:
            reasons.append("Positive Momentum")

        if features["volatility_score"] >= 70:
            reasons.append("Controlled Volatility")

        if features["liquidity_score"] >= 70:
            reasons.append("High Liquidity")

        if len(reasons) == 0:
            reasons.append("No strong factors detected")

        return reasons