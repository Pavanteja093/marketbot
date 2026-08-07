import pandas as pd


def snapshot(df):

    return {

        "average":

            round(

                df["intelligence_score"].mean(),

                2

            ),

        "median":

            round(

                df["intelligence_score"].median(),

                2

            ),

        "maximum":

            round(

                df["intelligence_score"].max(),

                2

            ),

        "minimum":

            round(

                df["intelligence_score"].min(),

                2

            )

    }