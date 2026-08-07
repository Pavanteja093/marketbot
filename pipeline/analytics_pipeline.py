"""
MarketBot Analytics Pipeline

Runs every analytics module in order.
"""

from analytics.market_regime_v2 import MarketRegimeV2


def run_analytics_pipeline():

    print("\n" + "=" * 60)
    print("ANALYTICS PIPELINE")
    print("=" * 60)

    try:
        print("Running Market Regime...")
        MarketRegimeV2().run()
        print("✓ Market Regime Complete")

    except Exception as e:
        print(f"✗ Market Regime Failed: {e}")

    # Future modules
    #
    # FeatureEngine().run()
    # IntelligenceEngine().run()
    # MarketBrain().run()
    # ProbabilityEngine().run()

    print("=" * 60)
    print("Analytics Pipeline Complete")
    print("=" * 60)