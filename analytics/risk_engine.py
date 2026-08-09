def calculate_risk(features):

    volatility = features["volatility_score"]

    liquidity = features["liquidity_score"]

    if volatility >= 80 and liquidity >= 70:

        return "LOW"

    elif volatility >= 60:

        return "MEDIUM"

    return "HIGH"