def calibrate(probability):

    probability = max(

        0,

        min(

            probability,

            100

        )

    )

    return round(

        probability,

        2

    )