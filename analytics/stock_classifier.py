def classify_stock(score):

    if score >= 85:
        return "Leader"

    if score >= 70:
        return "Strong"

    if score >= 55:
        return "Neutral"

    if score >= 40:
        return "Weak"

    return "Avoid"