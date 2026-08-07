import pandas as pd


def calculate_win_probability(history_df):

    if len(history_df) < 30:
        return 50

    wins = (
        history_df["change_pct"] > 0
    ).sum()

    probability = wins / len(history_df)

    return round(probability * 100, 2)