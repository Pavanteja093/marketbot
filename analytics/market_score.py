from analytics.market_health import market_health
from analytics.market_sentiment import sentiment


def market_score():

    health = market_health()
    mood = sentiment()

    score = 50

    if "STRONG" in str(health):
        score += 20

    if "POSITIVE" in str(health):
        score += 10

    if mood == "Bullish":
        score += 20

    elif mood == "Bearish":
        score -= 20

    print()

    print("=" * 60)
    print("OVERALL MARKET SCORE")
    print("=" * 60)

    print(score)

    return score


if __name__ == "__main__":
    market_score()