from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(
    str(BASE_DIR / "analytics")
)

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
# REPORT
# ----------------------------------

print("\n" + "=" * 70)
print("MARKET INTELLIGENCE REPORT")
print("=" * 70)

# ----------------------------------
# MARKET REGIME
# ----------------------------------

print("\nMARKET REGIME")
print("-" * 30)

print(
    f"Regime : {regime['regime']}"
)

print(
    f"NIFTY Change : "
    f"{regime['nifty_change']}%"
)

print(
    f"A/D Ratio : "
    f"{regime['ad_ratio']}"
)

# ----------------------------------
# SECTOR LEADERS
# ----------------------------------

print("\nSECTOR LEADERS")
print("-" * 30)

print(
    sectors.head(3)
    .to_string(index=False)
)

# ----------------------------------
# FII / DII
# ----------------------------------

print("\nFII / DII")
print("-" * 30)

if fii["available"]:

    print(
        f"FII : "
        f"{fii['fii_view']}"
    )

    print(
        f"DII : "
        f"{fii['dii_view']}"
    )

    print(
        f"FII Net : "
        f"{fii['fii_net']}"
    )

    print(
        f"DII Net : "
        f"{fii['dii_net']}"
    )

# ----------------------------------
# TOP STOCKS
# ----------------------------------

print("\nTOP STOCKS")
print("-" * 30)

print(
    stocks[
        [
            "grade",
            "symbol",
            "sector",
            "total_score"
        ]
    ]
    .head(10)
    .to_string(index=False)
)