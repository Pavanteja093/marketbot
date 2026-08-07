import pandas as pd


def regime_learning(df):

    return (

        df.groupby("regime")

        ["return_5d"]

        .mean()

        .round(2)

    )