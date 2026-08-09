def explain_decision(
    regime,
    confidence,
    risk,
    recommendation
):

    print("\nDECISION SUMMARY")
    print("-" * 40)

    print("Regime :", regime)

    print("Confidence :", confidence)

    print("Risk :", risk)

    print("Recommendation :", recommendation)

    print()

    if confidence >= 80:
        print("Reason : High confidence opportunity.")

    elif confidence >= 60:
        print("Reason : Moderate confidence. Monitor closely.")

    else:
        print("Reason : Weak setup. Avoid aggressive entries.")