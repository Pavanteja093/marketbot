from analytics.ranking_engine import build_rankings


def leaders():

    rankings = build_rankings()

    if rankings is None:

        return None

    return rankings.head(5)