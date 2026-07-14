import pandas as pd


def optimize_portfolio(signals):

    if len(signals) == 0:
        return signals

    portfolio = signals.head(5).copy()

    total_score = portfolio[
        "ranking_score"
    ].sum()

    portfolio["weight_pct"] = (

        portfolio["ranking_score"]

        / total_score

    ) * 100

    portfolio["weight_pct"] = (
        portfolio["weight_pct"]
        .round(2)
    )

    return portfolio