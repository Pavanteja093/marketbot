import pandas as pd


def expected_return(history_df, days=5):

    if len(history_df) < days + 1:
        return None

    start = history_df.iloc[-days - 1]["close"]
    end = history_df.iloc[-1]["close"]

    return round(((end - start) / start) * 100, 2)