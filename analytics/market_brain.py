from market_regime import get_market_regime
from sector_strength import get_sector_strength
from fii_dii_tracker import get_fii_dii
from stock_scoring import get_stock_scores


def get_market_brain():

    # ----------------------------------
    # LOAD DATA
    # ----------------------------------

    regime = get_market_regime()

    sectors = get_sector_strength()

    fii = get_fii_dii()

    stocks = get_stock_scores()

    # ----------------------------------
    # MARKET VIEW
    # ----------------------------------

    if (
        regime["regime"] == "BULLISH TREND"
        and fii["available"]
        and fii["fii_net"] > 0
    ):

        market_view = "Bullish"

    elif (
        regime["regime"] == "BEARISH TREND"
        and fii["available"]
        and fii["fii_net"] < 0
    ):

        market_view = "Bearish"

    else:

        market_view = "Neutral"

    # ----------------------------------
    # LEADING SECTOR
    # ----------------------------------

    leading_sector = sectors.iloc[0]["Sector"]

    # ----------------------------------
    # TOP STOCKS
    # ----------------------------------

    top_stocks = (
        stocks.head(5)["symbol"]
        .tolist()
    )

    # ----------------------------------
    # RISK SCORE
    # ----------------------------------

    risk_score = 50

    if regime["regime"] == "RANGE BOUND":

        risk_score += 10

    if (
        fii["available"]
        and fii["fii_net"] > 0
    ):

        risk_score -= 10

    risk_score = max(
        0,
        min(risk_score, 100)
    )

    # ----------------------------------
    # ACTION
    # ----------------------------------

    if market_view == "Bullish":

        action = "Look for long setups."

    elif market_view == "Bearish":

        action = "Focus on defensive trades."

    else:

        action = (
            "Prefer stock-specific opportunities."
        )

    # ----------------------------------
    # OUTPUT OBJECT
    # ----------------------------------

    brain = {

        "market_view": market_view,

        "market_regime": regime["regime"],

        "leading_sector": leading_sector,

        "risk_score": risk_score,

        "fii_flow": (
            fii["fii_view"]
            if fii["available"]
            else "Unavailable"
        ),

        "top_stocks": top_stocks,

        "action": action
    }

    return brain


# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    brain = get_market_brain()

    print("\n" + "=" * 60)
    print("MARKET BRAIN")
    print("=" * 60)

    print(
        f"\nMarket View      : "
        f"{brain['market_view']}"
    )

    print(
        f"Market Regime    : "
        f"{brain['market_regime']}"
    )

    print(
        f"Leading Sector   : "
        f"{brain['leading_sector']}"
    )

    print(
        f"FII Flow         : "
        f"{brain['fii_flow']}"
    )

    print(
        f"Risk Score       : "
        f"{brain['risk_score']}/100"
    )

    print("\nTOP FOCUS STOCKS")

    for stock in brain["top_stocks"]:

        print(f"- {stock}")

    print("\nACTION")

    print(brain["action"])