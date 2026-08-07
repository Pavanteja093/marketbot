from analytics.market_score import market_score


def market_risk():

    score = market_score()

    if score >= 80:
        risk = "LOW"

    elif score >= 60:
        risk = "MODERATE"

    elif score >= 40:
        risk = "HIGH"

    else:
        risk = "EXTREME"

    print()

    print("Market Risk :", risk)

    return risk


if __name__ == "__main__":
    market_risk()