from analytics.ranking_engine import build_rankings


def build_watchlist():

    rankings = build_rankings()

    if rankings is None:
        return

    watchlist = rankings.head(15)

    print("\nWATCHLIST")

    print(watchlist[
        [
            "rank",
            "index_name",
            "intelligence_score"
        ]
    ])

    return watchlist


if __name__ == "__main__":

    build_watchlist()