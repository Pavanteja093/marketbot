"""
Momentum Score

Computes momentum based on recent daily returns.

Output:
-------
momentum_score : 0-100
momentum_grade : A+ / A / B+ / B / C / D
"""

import pandas as pd


def calculate_momentum(df: pd.DataFrame):

    """
    Parameters
    ----------
    df
        Historical dataframe for ONE stock.
        Must contain:

            trade_date
            close

    Returns
    -------
    score
    grade
    """

    if len(df) < 10:
        return None, None

    df = df.sort_values("trade_date").copy()

    df["daily_return"] = df["close"].pct_change() * 100

    last_return = df["daily_return"].iloc[-1]

    avg3 = df["daily_return"].tail(3).mean()

    avg5 = df["daily_return"].tail(5).mean()

    avg10 = df["daily_return"].tail(10).mean()

    score = (
        last_return * 0.40
        + avg3 * 0.30
        + avg5 * 0.20
        + avg10 * 0.10
    )

    score = max(min(score * 10 + 50, 100), 0)

    if score >= 90:
        grade = "A+"

    elif score >= 80:
        grade = "A"

    elif score >= 70:
        grade = "B+"

    elif score >= 60:
        grade = "B"

    elif score >= 50:
        grade = "C"

    else:
        grade = "D"

    return round(score, 2), grade