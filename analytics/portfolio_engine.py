from analytics.portfolio_manager import portfolio_manager
from analytics.position_sizer import position_size
from analytics.risk_budget import risk_budget
from analytics.trade_planner import trade_planner
from analytics.exposure_manager import exposure_manager


def portfolio_engine():

    print("\n" + "=" * 70)
    print("PORTFOLIO ENGINE")
    print("=" * 70)

    portfolio_manager()

    print("\nPortfolio Summary")
    print("-" * 50)

    print("Maximum Positions : 10")

    print("Maximum Sector Exposure : 25%")

    print("Cash Reserve : 10%")

    print("Rebalance : Weekly")

    risk_budget()

    trade_planner()

    exposure_manager()