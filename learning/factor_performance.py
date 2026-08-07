import pandas as pd


def evaluate(df):

    cols = [

        "relative_strength",

        "trend_score",

        "momentum_score",

        "volatility_score",

        "liquidity_score"

    ]

    performance = {}

    for col in cols:

        performance[col] = round(

            df[col].corr(

                df["return_5d"]

            ),

            3

        )

    return performance