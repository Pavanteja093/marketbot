import pandas as pd


def market_breadth(rankings):

    advancing = (
        rankings["momentum_score"] > 50
    ).sum()

    declining = (
        rankings["momentum_score"] <= 50
    ).sum()

    return {

        "advancing": advancing,

        "declining": declining,

        "advance_decline_ratio":
            round(advancing / max(declining, 1), 2)

    }