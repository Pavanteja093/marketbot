def score_breakdown(features, weights):

    contributions = {}

    for factor, weight in weights.items():

        value = features.get(factor, 0)

        contributions[factor] = round(value * weight, 2)

    return dict(
        sorted(
            contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )
    )