def scan(df):

    return df[

        (df["intelligence_score"] >= 75)

        &

        (df["relative_strength"] >= 70)

        &

        (df["momentum_score"] >= 70)

    ]