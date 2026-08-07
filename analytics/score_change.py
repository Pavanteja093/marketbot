import pandas as pd


def score_change(df):

    if len(df) < 2:

        return 0

    return round(

        df.iloc[-1]["intelligence_score"]

        -

        df.iloc[-2]["intelligence_score"],

        2

    )