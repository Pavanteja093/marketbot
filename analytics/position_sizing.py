def suggested_position(confidence):

    if confidence >= 90:
        return "100%"

    elif confidence >= 80:
        return "75%"

    elif confidence >= 70:
        return "50%"

    elif confidence >= 60:
        return "25%"

    return "No Trade"