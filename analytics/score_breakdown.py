def explain_score(features):

    return {

        "Relative Strength":
            features["relative_strength"],

        "Momentum":
            features["momentum_score"],

        "Trend":
            features["trend_score"],

        "Volatility":
            features["volatility_score"],

        "Liquidity":
            features["liquidity_score"],

        "Overall":
            features["intelligence_score"]

    }