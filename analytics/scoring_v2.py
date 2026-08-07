def weighted_score(

    features,

    weights

):

    score = 0

    for factor, weight in weights.items():

        if factor in features:

            score += (

                features[factor]

                * weight

            )

    return round(score, 2)