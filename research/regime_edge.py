import pandas as pd


def regime_edge(df):

    return (

        df.groupby("regime")

        ["return_5d"]

        .mean()

        .sort_values(

            ascending=False

        )

    )