def calculate_quality(history_df):

    if len(history_df) < 60:
        return 50, "C"

    score = 100

    if history_df["close"].std() > history_df["close"].mean() * 0.15:
        score -= 20

    if history_df["change_pct"].abs().mean() > 3:
        score -= 20

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