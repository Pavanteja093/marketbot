import pandas as pd


def calculate_market_statistics(rankings):

    return {

        "stocks": len(rankings),

        "average_score":
            round(rankings["intelligence_score"].mean(), 2),

        "highest_score":
            round(rankings["intelligence_score"].max(), 2),

        "lowest_score":
            round(rankings["intelligence_score"].min(), 2),

        "average_momentum":
            round(rankings["momentum_score"].mean(), 2),

        "average_trend":
            round(rankings["trend_score"].mean(), 2),

        "average_rs":
            round(rankings["relative_strength"].mean(), 2),

        "average_liquidity":
            round(rankings["liquidity_score"].mean(), 2)

    }