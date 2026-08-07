from analytics.reason_engine import explain


def explain_rankings(df):

    df = df.copy()

    df["reasons"] = df.apply(

        explain,

        axis=1

    )

    return df