def confidence_score(probability, intelligence):

    score = (
        probability * 0.6 +
        intelligence * 0.4
    )

    return round(score, 2)