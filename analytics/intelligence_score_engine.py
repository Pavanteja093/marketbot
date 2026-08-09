def intelligence_score(features):

    score = (

        features["relative_strength"] * 0.25

        +

        features["momentum_score"] * 0.25

        +

        features["trend_score"] * 0.25

        +

        (features["pcr"] * 25)

    )

    return round(score, 2)