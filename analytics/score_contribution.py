def score_contribution(features, weights):
    """
    Returns the contribution of every factor
    towards the final intelligence score.
    """

    contributions = {}

    total = 0

    for factor, weight in weights.items():

        value = float(features.get(factor, 0))

        contribution = value * weight

        contributions[factor] = round(contribution, 2)

        total += contribution

    contributions = dict(

        sorted(

            contributions.items(),

            key=lambda item: item[1],

            reverse=True

        )

    )

    print("\n" + "=" * 60)
    print("SCORE CONTRIBUTION")
    print("=" * 60)

    for factor, value in contributions.items():

        pct = 0

        if total != 0:

            pct = value / total * 100

        print(

            f"{factor:<25}"

            f"{value:>8.2f}"

            f"   ({pct:>5.1f}%)"

        )

    return contributions