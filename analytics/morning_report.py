from analytics.market_brain import get_market_brain
from analytics.report_engine import print_market_report
from analytics.trading_playbook import get_trading_playbook


def print_playbook(playbook):

    print("\n" + "=" * 70)
    print("TODAY'S TRADING PLAYBOOK")
    print("=" * 70)

    print(f"Index View        : {playbook['index_view']}")
    print(f"Options View      : {playbook['options_view']}")
    print(f"Market Bias       : {playbook['market_bias']}")

    sector = playbook["strongest_sector"]

    print(
        f"Strongest Sector  : "
        f"{sector['sector']} ({sector['strength']:.2f}%)"
    )

    print(
        f"Confidence Score  : "
        f"{playbook['confidence_score']}/100"
    )

    print("\nFocus Stocks")

    for stock in playbook["focus_stocks"]:
        print(f"  • {stock}")

    print("=" * 70)


def run_morning_report():

    print("\n")
    print("=" * 80)
    print("               MARKETBOT V1 MORNING REPORT")
    print("=" * 80)

    results = get_market_brain()

    for symbol in results:

        print_market_report(results[symbol])

    playbook = get_trading_playbook()

    print_playbook(playbook)

    print("\nMorning Report Completed Successfully")


if __name__ == "__main__":
    run_morning_report()