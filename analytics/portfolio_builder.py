import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR))

from analytics.alpha_signal_v3 import alpha_signal_v3
from analytics.portfolio_optimizer import optimize_portfolio


def build_portfolio():

    signals = alpha_signal_v3()

    if signals is None or len(signals) == 0:

        print("No portfolio candidates.")

        return signals

    portfolio = optimize_portfolio(signals)

    print("\n" + "=" * 70)
    print("PORTFOLIO BUILDER")
    print("=" * 70)

    print(
        portfolio[
            [
                "symbol",
                "ranking_score",
                "weight_pct"
            ]
        ]
        .round(3)
        .to_string(index=False)
    )

    print("\n" + "=" * 70)

    return portfolio


if __name__ == "__main__":

    build_portfolio()