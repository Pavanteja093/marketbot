def composite_confidence(

    intelligence,

    probability,

    regime

):

    return round(

        intelligence * 0.4 +

        probability * 0.4 +

        regime * 0.2,

        2

    )