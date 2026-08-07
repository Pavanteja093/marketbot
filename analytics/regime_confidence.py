def regime_confidence(regime):

    table = {

        "Bull":95,

        "Trending Bull":90,

        "Sideways":70,

        "Volatile":60,

        "Bear":85,

        "Trending Bear":90

    }

    return table.get(

        regime,

        50

    )