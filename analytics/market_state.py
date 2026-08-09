def market_state(features):

    if features["market_quality"] >= 75:

        return "Excellent"

    elif features["market_quality"] >= 60:

        return "Healthy"

    elif features["market_quality"] >= 45:

        return "Average"

    return "Weak"