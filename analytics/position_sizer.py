import pandas as pd


def position_size(df):

    df = df.copy()

    total_score = df["intelligence_score"].sum()

    df["allocation_pct"] = (
        df["intelligence_score"]
        /
        total_score
        *
        100
    ).round(2)

    return df[
        [
            "symbol",
            "intelligence_score",
            "allocation_pct"
        ]
    ]


if __name__ == "__main__":

    print("Import into portfolio manager.")