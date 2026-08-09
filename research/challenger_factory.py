from copy import deepcopy


def build_challenger(
    weights,
    performance=None,
    max_adjustment=0.03
):

    if not weights:
        raise ValueError(
            "weights cannot be empty"
        )

    challenger = deepcopy(weights)

    # -------------------------------------------------------
    # If factor performance is unavailable,
    # return a normalized copy rather than inventing random
    # information.
    # -------------------------------------------------------

    if not performance:

        total = sum(
            max(float(v), 0.0)
            for v in challenger.values()
        )

        if total <= 0:

            raise ValueError(
                "Weight total must be positive."
            )

        challenger = {
            k: round(
                max(float(v), 0.0) / total,
                4
            )
            for k, v in challenger.items()
        }

    else:

        scores = {}

        for factor in weights:

            value = performance.get(
                factor,
                0
            )

            scores[factor] = float(value)

        # ---------------------------------------------------
        # Performance adjustment.
        # Positive performance receives a small increase.
        # Negative performance receives a small decrease.
        # ---------------------------------------------------

        for factor, weight in weights.items():

            signal = scores.get(
                factor,
                0
            )

            adjustment = max(
                -max_adjustment,
                min(
                    max_adjustment,
                    signal * max_adjustment
                )
            )

            challenger[factor] = max(
                0,
                float(weight) + adjustment
            )

        total = sum(
            challenger.values()
        )

        if total <= 0:

            raise ValueError(
                "Challenger weights became invalid."
            )

        challenger = {
            k: round(
                v / total,
                4
            )
            for k, v in challenger.items()
        }

    print("\n" + "=" * 70)
    print("MARKETBOT CHALLENGER MODEL")
    print("=" * 70)

    for factor, weight in challenger.items():

        print(
            f"{factor:<25}{weight:.4f}"
        )

    return challenger