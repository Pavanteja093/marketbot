def decay(old_weight,
          new_weight,
          alpha=0.2):

    return round(

        old_weight * (1 - alpha)

        +

        new_weight * alpha,

        4

    )