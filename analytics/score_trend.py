import pandas as pd


def score_trend(df):

    if len(df) < 5:

        return "UNKNOWN"

    last = df.tail(5)

    first = last.iloc[0]["intelligence_score"]

    latest = last.iloc[-1]["intelligence_score"]

    if latest > first:

        return "IMPROVING"

    elif latest < first:

        return "WEAKENING"

    else:

        return "STABLE"