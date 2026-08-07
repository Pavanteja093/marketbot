def opportunities(df):

    return (

        df[

            df["intelligence_score"] >= 70

        ]

    )