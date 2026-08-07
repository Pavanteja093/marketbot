from analytics.signal_generator import generate_signal
from analytics.confidence_engine import confidence_score
from analytics.risk_engine import calculate_risk


def explain(stock):

    signal = generate_signal(
        stock["intelligence_score"]
    )

    confidence = confidence_score(
        probability=stock["intelligence_score"],
        intelligence=stock["intelligence_score"]
    )

    risk = calculate_risk(
        stock["volatility_score"]
    )

    return {
        "signal": signal,
        "confidence": confidence,
        "risk": risk,
        "summary":
            f"{stock['index_name']} | "
            f"Signal: {signal} | "
            f"Confidence: {confidence} | "
            f"Risk: {risk}"
    }


if __name__ == "__main__":
    print("Explainability Engine Ready")