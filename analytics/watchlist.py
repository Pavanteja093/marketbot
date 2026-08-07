def build_watchlist(df):

    return (

        df

        .sort_values(

            "intelligence_score",

            ascending=False

        )

        .head(20)

    )