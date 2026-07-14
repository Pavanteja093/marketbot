import os
from services.market_service import (
    get_direction,
    get_regime,
    get_decision,
)


def clear():
    os.system("cls")


def header():
    clear()
    print("=" * 70)
    print("                 MARKETBOT v1.0")
    print("=" * 70)


def update_market():
    
    import os

    os.system("python automation/run_daily_update.py")

    input("\nPress ENTER...")


def analyze_market():

    import os

    os.system("python -m analytics.market_brain")

    input("\nPress ENTER...")


def run_direction():

    response = get_direction()

    if response is None:

        print("\nNo market data found.")

    else:

        state, result = response

        print("\n" + "=" * 60)
        print("MARKETBOT DIRECTION MODEL")
        print("=" * 60)

        print("Symbol      :", state.symbol)
        print("Direction   :", result["bias"])
        print("Confidence  :", result["confidence"])
        print("Trade Score :", result["score"])
        print("Risk        :", result["risk"])
        print("Trade       :", result["trade"])
        print("Strategy    :", result["strategy"])

        print("\nProbabilities")
        print("-" * 60)

        print(f"Bullish : {result['bullish_probability']}%")
        print(f"Bearish : {result['bearish_probability']}%")
        print(f"Neutral : {result['neutral_probability']}%")

        print("\nReasons")
        print("-" * 60)

        for reason in result["reasons"]:
            print("✓", reason)

    input("\nPress ENTER...")


def run_regime():

    response = get_regime()

    if response is None:

        print("\nNo market data found.")

    else:

        state, result = response

        print("\n" + "=" * 60)
        print("MARKETBOT REGIME MODEL")
        print("=" * 60)

        print("Symbol      :", state.symbol)
        print("Regime      :", result["regime"])
        print("Confidence  :", result["confidence"])
        print("Strategy    :", result["strategy"])

    input("\nPress ENTER...")


def run_decision():

    response = get_decision()

    if response is None:

        print("\nNo market data found.")

    else:

        state, result = response

        print("\n" + "=" * 60)
        print("MARKETBOT DECISION MODEL")
        print("=" * 60)

        print("Symbol      :", state.symbol)
        print("Direction   :", result["prediction"])
        print("Regime      :", result["regime"])
        print("Trade       :", result["trade"])
        print("Strategy    :", result["strategy"])
        print("Risk        :", result["risk"])
        print("Confidence  :", result["confidence"])

        print("\nReasons")
        print("-" * 60)

        for reason in result["reasons"]:
            print("✓", reason)

    input("\nPress ENTER...")


def dashboard():
    
    import os

    os.system("streamlit run dashboard/app.py")

    input("\nPress ENTER...")


def menu():

    while True:

        header()

        print("1. Update Market Data")
        print("2. Analyze Market")
        print("3. Direction Model")
        print("4. Regime Model")
        print("5. Decision Model")
        print("6. Dashboard")
        print("7. Exit")

        print()

        choice = input("Select Option : ")

        if choice == "1":
            update_market()

        elif choice == "2":
            analyze_market()

        elif choice == "3":
            run_direction()

        elif choice == "4":
            run_regime()

        elif choice == "5":
            run_decision()

        elif choice == "6":
            dashboard()

        elif choice == "7":
            break

        else:
            print("\nInvalid Choice.")
            input("\nPress ENTER...")


if __name__ == "__main__":
    menu()