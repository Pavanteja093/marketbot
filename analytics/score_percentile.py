import pandas as pd


def percentile(df):

    latest = df.iloc[-1]["intelligence_score"]

    pct = (

        df["intelligence_score"]

        < latest

    ).mean() * 100

    return round(pct,2)