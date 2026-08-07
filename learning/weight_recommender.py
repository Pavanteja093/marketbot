def recommend(performance):

    weights = {}

    total = sum(

        abs(v)

        for v in performance.values()

    )

    if total == 0:

        return weights

    for factor, score in performance.items():

        weights[factor] = round(

            abs(score) / total,

            3

        )

    return weights