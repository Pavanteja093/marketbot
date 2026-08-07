from analytics.ranking_engine import build_rankings


def generate_watchlist():

    rankings = build_rankings()

    if rankings is None:

        return

    watchlist = rankings.head(15)

    print("\nToday's Watchlist")

    print(watchlist[
        [
            "overall_rank",
            "index_name",
            "intelligence_score"
        ]
    ])


if __name__ == "__main__":

    generate_watchlist()