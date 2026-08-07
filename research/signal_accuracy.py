import pandas as pd


def accuracy(df):

    correct = (

        df["prediction"]

        ==

        df["actual"]

    )

    return round(

        correct.mean() * 100,

        2

    )