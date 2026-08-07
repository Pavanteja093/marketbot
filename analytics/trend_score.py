import pandas as pd


def calculate_trend(df: pd.DataFrame):

    """
    Returns
    -------
    trend_score
    trend_grade
    """

    if len(df) < 20:
        return None, None

    df = df.sort_values("trade_date")

    sma5 = df["close"].rolling(5).mean().iloc[-1]
    sma10 = df["close"].rolling(10).mean().iloc[-1]
    sma20 = df["close"].rolling(20).mean().iloc[-1]

    score = 50

    if sma5 > sma10:
        score += 20

    if sma10 > sma20:
        score += 20

    if df["close"].iloc[-1] > sma20:
        score += 10

    score = min(score, 100)

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

    return score, grade