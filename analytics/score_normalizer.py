def normalize(score):

    if score is None:
        return 0

    if score < 0:
        return 0

    if score > 100:
        return 100

    return round(score, 2)