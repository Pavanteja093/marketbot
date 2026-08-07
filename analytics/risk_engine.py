def calculate_risk(volatility_score):

    if volatility_score >= 80:
        return "LOW"

    elif volatility_score >= 60:
        return "MEDIUM"

    return "HIGH"