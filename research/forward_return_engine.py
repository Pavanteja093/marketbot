import pandas as pd


def calculate_forward_returns(df):

    df = df.copy()

    df["future_return_5"] = (
        df["close"]
        .shift(-5)
        /
        df["close"]
        - 1
    ) * 100

    df["future_return_10"] = (
        df["close"]
        .shift(-10)
        /
        df["close"]
        - 1
    ) * 100

    df["future_return_20"] = (
        df["close"]
        .shift(-20)
        /
        df["close"]
        - 1
    ) * 100

    return df