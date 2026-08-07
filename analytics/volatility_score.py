import pandas as pd


def calculate_volatility(df: pd.DataFrame):

    """
    Volatility Score (0-100)

    Uses rolling daily returns.
    """

    if len(df) < 20:
        return None, None

    df = df.sort_values("trade_date")

    returns = df["close"].pct_change()

    volatility = returns.rolling(20).std().iloc[-1]

    score = max(0, min(100, 100 - volatility * 1000))

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