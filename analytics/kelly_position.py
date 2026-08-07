def kelly(probability,
          reward_risk):

    p = probability / 100

    q = 1 - p

    return max(

        0,

        round(

            (

                p * reward_risk - q

            )

            /

            reward_risk,

            3

        )

    )