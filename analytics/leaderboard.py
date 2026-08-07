from analytics.ranking_engine import build_rankings


def leaderboard():

    rankings = build_rankings()

    if rankings is None:
        return

    print()

    print("=" * 60)
    print("MARKET LEADERBOARD")
    print("=" * 60)

    print(rankings.head(20))

    print()

    print("Average Intelligence :", round(rankings["intelligence_score"].mean(),2))

    print("Highest Score :", rankings["intelligence_score"].max())

    print("Lowest Score :", rankings["intelligence_score"].min())


if __name__ == "__main__":
    leaderboard()