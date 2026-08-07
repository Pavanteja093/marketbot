import pandas as pd


class FactorAnalysis:

    def summarize(self, df):

        return {

            "stocks_analyzed": len(df),

            "average_score":
                round(
                    df["intelligence_score"].mean(),
                    2
                ),

            "median_score":
                round(
                    df["intelligence_score"].median(),
                    2
                ),

            "highest_score":
                round(
                    df["intelligence_score"].max(),
                    2
                ),

            "lowest_score":
                round(
                    df["intelligence_score"].min(),
                    2
                )

        }

    def top_ranked(self, df, n=10):

        return df.sort_values(
            "intelligence_score",
            ascending=False
        ).head(n)