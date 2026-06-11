# analytics/market_explainer.py

from global_markets import get_global_markets


def get_market_explanations():

    markets = get_global_markets()

    explanations = []

    for _, row in markets.iterrows():

        asset = row["Asset"]

        change = row["Change %"]

        # ----------------------------------
        # CRUDE
        # ----------------------------------

        if asset == "CRUDE":

            if change < 0:

                explanations.append({

                    "topic": "Crude Oil",

                    "change": change,

                    "impact":
                    (
                        "Lower crude reduces "
                        "India's import bill, "
                        "eases inflation and "
                        "supports consumption."
                    ),

                    "bias": "Bullish for India"
                })

            else:

                explanations.append({

                    "topic": "Crude Oil",

                    "change": change,

                    "impact":
                    (
                        "Higher crude increases "
                        "inflation pressure and "
                        "raises import costs."
                    ),

                    "bias": "Bearish for India"
                })

        # ----------------------------------
        # DOLLAR
        # ----------------------------------

        elif asset == "DOLLAR_INDEX":

            if change > 0:

                explanations.append({

                    "topic": "US Dollar",

                    "change": change,

                    "impact":
                    (
                        "A stronger dollar can "
                        "pressure emerging markets "
                        "but support exporters."
                    ),

                    "bias": "Positive for IT"
                })

        # ----------------------------------
        # NASDAQ
        # ----------------------------------

        elif asset == "NASDAQ":

            if change < -1:

                explanations.append({

                    "topic": "NASDAQ",

                    "change": change,

                    "impact":
                    (
                        "Weak US technology stocks "
                        "may create risk-off sentiment."
                    ),

                    "bias": "Short-Term Negative"
                })

    return explanations


# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    explanations = get_market_explanations()

    print("\n" + "=" * 60)
    print("MARKET EXPLAINER")
    print("=" * 60)

    for item in explanations:

        print(f"\n{item['topic']}")
        print("-" * 30)

        print(
            f"Change : "
            f"{item['change']}%"
        )

        print(
            f"Impact : "
            f"{item['impact']}"
        )

        print(
            f"Bias   : "
            f"{item['bias']}"
        ) 