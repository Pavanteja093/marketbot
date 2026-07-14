def print_market_report(result):

    print("\n" + "=" * 70)

    print(result["symbol"])

    print("=" * 70)

    print(f"Spot Price      : {result['spot_price']:.2f}")

    print(f"Real PCR        : {result['real_pcr']:.2f}")

    print(f"Support         : {result['support']}")

    print(f"Resistance      : {result['resistance']}")

    print(f"Reward/Risk     : {result['reward_risk']:.2f}")

    print(f"Max Pain        : {result['max_pain']}")

    print(f"Market Location : {result['market_location']}")

    print(f"Average IV      : {result['avg_iv']:.2f}")

    print(f"Expected Move   : ±{result['expected_move']:.2f}")

    print(
        f"Expected Range  : "
        f"{result['lower_target']:.2f} - "
        f"{result['upper_target']:.2f}"
    )

    print(f"Delta           : {result['delta']:.4f}")

    print(f"Gamma           : {result['gamma']:.4f}")

    print(f"Theta           : {result['theta']:.4f}")

    print(f"Vega            : {result['vega']:.4f}")

    print()

    print("Market Bias")

    print(result["bias"])

    print()

    print(f"Trade Quality   : {result['score']}/100")

    print(f"Risk            : {result['risk']}")

    print(f"Trade Decision  : {result['trade']}")

    print()

    print("Recommended Strategy")

    print(result["strategy"])

    print()

    print(f"Confidence      : {result['confidence']}%")

    print()

    print("Reasons")

    for reason in result["reasons"]:

        print("-", reason)