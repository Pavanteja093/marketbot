import pandas as pd


def calculate_importance(df):

    cols = [

        "relative_strength",

        "trend_score",

        "momentum_score",

        "volatility_score",

        "liquidity_score"

    ]

    return df[cols].mean().sort_values(
        ascending=False
    )