def confidence_score(features):

    score = (

        features["probability"] * 0.50 +

        features["intelligence_score"] * 0.30 +

        features["quality_score"] * 0.20

    )

    return round(score, 2)