import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR))

from analytics.alpha_signal_v3 import alpha_signal_v3
from analytics.probability_engine import get_signal_probability
from analytics.portfolio_builder import build_portfolio


def master_alpha_report():

    print("\n")
    print("=" * 70)
    print("MARKETBOT MASTER ALPHA REPORT")
    print("=" * 70)

    print("\nGENERATING SIGNALS...")
    signals = alpha_signal_v3()

    print("\nGENERATING PROBABILITIES...")
    probability = get_signal_probability()

    print("\nBUILDING PORTFOLIO...")
    portfolio = build_portfolio()

    print("\n")
    print("=" * 70)
    print("ALPHA SUMMARY")
    print("=" * 70)

    top_pick = portfolio.iloc[0]

    print(
        f"\nTop pick        : {top_pick['symbol']}"
    )

    print(
        f"Expected Return        : {top_pick['expected_return']}% "  
    )

    print(
        f"Confidence      : {top_pick['confidence']}"
    )

    print(
        f"Market Regime   : {top_pick['regime']}"
    )

    print(
        f"\nSignals Today   : {len(signals)}"
    )

    print(
        f"Portfolio Size  : {len(portfolio)}"
    )

    print("\n")
    print("=" * 70)


if __name__ == "__main__":

    master_alpha_report()