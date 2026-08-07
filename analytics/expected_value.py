def expected_value(probability,
                   reward,
                   risk):

    p = probability / 100

    return (

        p * reward

    ) - (

        (1 - p) * risk

    )