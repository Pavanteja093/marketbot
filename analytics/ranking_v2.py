import pandas as pd


def overall_rank(df):

    df = df.copy()

    df = df.sort_values(

        "confidence",

        ascending=False

    )

    df["overall_rank"] = range(

        1,

        len(df) + 1

    )

    return df