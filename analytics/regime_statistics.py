def summarize(df):

    return (

        df

        .groupby("market_regime")

        .size()

        .reset_index(name="count")

    )