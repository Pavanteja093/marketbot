from stock_scoring import get_stock_scores


def get_stock_reasons():

    stocks = get_stock_scores()

    top_stocks = stocks.head(10)

    reasons = []

    for _, row in top_stocks.iterrows():

        stock = row["symbol"]

        sector = row["sector"]

        score = round(
            row["total_score"],
            2
        )

        price_change = round(
            row["change_pct"],
            2
        )

        reason_text = []

        # ----------------------------------
        # MOMENTUM
        # ----------------------------------

        if price_change > 1:

            reason_text.append(
                "Strong price momentum"
            )

        elif price_change > 0:

            reason_text.append(
                "Positive price action"
            )

        # ----------------------------------
        # SCORE
        # ----------------------------------

        if score >= 70:

            reason_text.append(
                "High composite score"
            )

        elif score >= 60:

            reason_text.append(
                "Above-average score"
            )

        # ----------------------------------
        # SECTOR
        # ----------------------------------

        reason_text.append(
            f"Belongs to {sector} sector"
        )

        reasons.append({

            "symbol": stock,

            "sector": sector,

            "score": score,

            "change_pct": price_change,

            "reason":
                ", ".join(reason_text)
        })

    return reasons


# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    stocks = get_stock_reasons()

    print("\n" + "=" * 70)
    print("STOCK REASON ENGINE")
    print("=" * 70)

    for stock in stocks:

        print(
            f"\n{stock['symbol']}"
        )

        print(
            f"Sector : "
            f"{stock['sector']}"
        )

        print(
            f"Score  : "
            f"{stock['score']}"
        )

        print(
            f"Reason : "
            f"{stock['reason']}"
        )