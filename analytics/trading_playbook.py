from analytics.market_regime import get_market_regime
from analytics.sector_strength import get_sector_strength
from analytics.fii_dii_tracker import get_fii_dii
from analytics.stock_scoring import get_stock_scores


def get_trading_playbook():

    # ----------------------------------
    # LOAD DATA
    # ----------------------------------

    regime = get_market_regime()

    sectors = get_sector_strength()

    fii = get_fii_dii()

    stocks = get_stock_scores()

    # ----------------------------------
    # INDEX VIEW
    # ----------------------------------

    if regime["regime"] == "BULLISH TREND":

        index_view = "Bullish"

    elif regime["regime"] == "BEARISH TREND":

        index_view = "Bearish"

    else:

        index_view = "Range Bound"

    # ----------------------------------
    # OPTIONS VIEW
    # ----------------------------------

    if regime["regime"] == "RANGE BOUND":

        options_view = (
            "Prefer Option Selling / "
            "Non-Directional Strategies"
        )

    elif regime["regime"] == "BULLISH TREND":

        options_view = (
            "Bull Call Spread / "
            "Call Buying"
        )

    else:

        options_view = (
            "Bear Put Spread / "
            "Put Buying"
        )

    market_bias = regime["regime"]


    # ----------------------------------
    # SWING VIEW
    # ----------------------------------

    strongest_sector = {
        "sector": sectors.iloc[0]["Sector"],
        "strength": sectors.iloc[0]["Average Change %"]
    }

    focus_stocks = (
        stocks.head(5)["symbol"]
              .tolist()
    )

    # ----------------------------------
    # CONFIDENCE SCORE
    # ----------------------------------

    confidence = 50

    if fii["available"]:

        if fii["fii_net"] > 0:

            confidence += 10

        else:

            confidence -= 10

    if regime["regime"] == "BULLISH TREND":

        confidence += 20

    elif regime["regime"] == "BEARISH TREND":

        confidence += 20

    # ----------------------------------
    # Sector Strength
    # ----------------------------------

    if len(sectors) > 0:

        top_strength = sectors.iloc[0]["Average Change %"]

        if top_strength >= 1.0:
            confidence += 10

        elif top_strength <= -1.0:
            confidence -= 10

    confidence = max(0, min(confidence, 100))

    playbook = {

        "index_view": index_view,

        "options_view": options_view,

        "market_bias": market_bias,

        "strongest_sector": strongest_sector,

        "confidence_score": confidence,

        "focus_stocks": focus_stocks
    }

    return playbook

# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    playbook = get_trading_playbook()

    print("\n" + "=" * 60)
    print("TRADING PLAYBOOK")
    print("=" * 60)
    
    print(
        f"\nINDEX VIEW : "
        f"{playbook['index_view']}"
    )

    print(
        f"OPTIONS VIEW : "
        f"{playbook['options_view']}"
    )

    sector = playbook["strongest_sector"]

    print(
        f"STRONGEST SECTOR : "
        f"{sector['sector']} ({sector['strength']:.2f})"
    )

    print(
        f"CONFIDENCE SCORE : "
        f"{playbook['confidence_score']}/100"
    )

    print("\nFOCUS STOCKS")

    for stock in playbook["focus_stocks"]:

        print(f"- {stock}")