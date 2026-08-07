import pandas as pd


def detect_market_regime(rankings):

    avg_score = rankings["intelligence_score"].mean()

    if avg_score >= 80:
        return "Strong Bull"

    elif avg_score >= 65:
        return "Bull"

    elif avg_score >= 50:
        return "Sideways"

    elif avg_score >= 35:
        return "Bear"

    return "Strong Bear"