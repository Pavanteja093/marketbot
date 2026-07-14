from market_regime import get_market_regime
from sector_strength import get_sector_strength
from fii_dii_tracker import get_fii_dii
from analytics.stock_scoring import get_stock_scores

# ----------------------------------
# LOAD DATA
# ----------------------------------

regime = get_market_regime()

sectors = get_sector_strength()

fii = get_fii_dii()

stocks = get_stock_scores()

# ----------------------------------
# INTERPRETATION
# ----------------------------------

market_view = "Neutral"

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

strongest_sector = sectors.iloc[0]["Sector"]

focus_stocks = (
    stocks.head(5)["symbol"]
          .tolist()
)

# ----------------------------------
# OUTPUT
# ----------------------------------

print("\n" + "=" * 60)
print("MARKET OUTLOOK")
print("=" * 60)

print(
    f"\nMarket View : "
    f"{market_view}"
)

print(
    f"Market Regime : "
    f"{regime['regime']}"
)

print(
    f"Strongest Sector : "
    f"{strongest_sector}"
)

if fii["available"]:

    print(
        f"FII Flow : "
        f"{fii['fii_view']}"
    )

print("\nFOCUS STOCKS")

for stock in focus_stocks:

    print(
        f"- {stock}"
    )