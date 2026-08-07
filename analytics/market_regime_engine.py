import pandas as pd


def detect_market_regime(rankings):

    avg = rankings["intelligence_score"].mean()

    if avg >= 70:
        regime = "Bull"

    elif avg >= 55:
        regime = "Neutral"

    else:
        regime = "Bear"

    return {
        "average_score": round(avg, 2),
        "regime": regime
    }


if __name__ == "__main__":

    print("Market Regime Engine")