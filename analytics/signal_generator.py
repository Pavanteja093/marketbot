def generate_signal(score):

    if score >= 80:
        return "STRONG BUY"

    elif score >= 65:
        return "BUY"

    elif score >= 45:
        return "HOLD"

    elif score >= 30:
        return "SELL"

    return "STRONG SELL"