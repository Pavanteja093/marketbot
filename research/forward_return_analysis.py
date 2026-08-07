import pandas as pd


def future_return(df, days=5):

    df = df.copy()

    df["future_return"] = (
        df["close"]
        .shift(-days)
        .sub(df["close"])
        .div(df["close"])
        * 100
    )

    return df