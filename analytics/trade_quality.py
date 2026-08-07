def trade_quality(confidence,
                  risk):

    if confidence >= 85 and risk == "LOW":
        return "A+"

    if confidence >= 75:
        return "A"

    if confidence >= 65:
        return "B"

    if confidence >= 50:
        return "C"

    return "Avoid"