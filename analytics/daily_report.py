import pandas as pd

from analytics.ranking_engine import build_rankings
from analytics.market_health import market_health
from analytics.market_sentiment import sentiment
from analytics.market_statistics import calculate_market_statistics


def generate_report():

    rankings = build_rankings()

    if rankings is None or rankings.empty:
        print("No ranking data.")
        return

    stats = calculate_market_statistics(rankings)

    print("\n" + "=" * 70)
    print("MARKETBOT DAILY REPORT")
    print("=" * 70)

    print("\nMARKET STATISTICS")
    print("-" * 70)

    for key, value in stats.items():
        print(f"{key:<25} {value}")

    print("\nTOP 10 STOCKS")
    print("-" * 70)

    print(
        rankings[
            [
                "overall_rank",
                "index_name",
                "intelligence_score"
            ]
        ].head(10)
    )

    if "confidence" in rankings.columns:

        print("\nTOP 5 HIGHEST CONFIDENCE")
        print("-" * 70)

        print(

            rankings

            .sort_values(

                "confidence",

                ascending=False

            )[
                [
                    "index_name",
                    "confidence"
                ]
            ].head(5)

        )

    print("\nMARKET HEALTH")
    print("-" * 70)
    print(market_health())

    from analytics.sector_rankings import build_sector_rankings

    print()
    print("=" * 60)
    print("TOP SECTORS")
    print("=" * 60)

    print(build_sector_rankings())

    print("\nMARKET SENTIMENT")
    print("-" * 70)
    print(sentiment())

    print("\n" + "=" * 70)


if __name__ == "__main__":
    generate_report()