import pandas as pd


def calculate_accuracy(df):

    if len(df) == 0:
        return 0

    correct = (
        df["prediction"] == df["actual"]
    ).sum()

    return round(correct / len(df) * 100, 2)