import pandas as pd


def detect_regime(features):
    """
    Determine the current market regime from
    intelligence score and volatility.
    """

    intelligence = features["intelligence_score"]
    volatility = features["volatility_score"]

    if intelligence >= 70 and volatility <= 40:
        return "STRONG BULL"

    elif intelligence >= 60:
        return "BULL"

    elif intelligence >= 45:
        return "SIDEWAYS"

    elif intelligence >= 30:
        return "BEAR"

    return "STRONG BEAR"


if __name__ == "__main__":

    sample = {
        "intelligence_score": 68,
        "volatility_score": 32
    }

    print(detect_regime(sample))