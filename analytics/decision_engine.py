from analytics.market_regime import detect_regime
from analytics.confidence_engine import confidence_score
from analytics.risk_engine import calculate_risk


def make_decision(features):

    # -----------------------------------------
    # MARKET REGIME
    # -----------------------------------------

    regime = detect_regime(
        features
    )

    # -----------------------------------------
    # CONFIDENCE
    # -----------------------------------------

    confidence = confidence_score(
        features
    )

    # -----------------------------------------
    # RISK
    # -----------------------------------------

    risk = calculate_risk(
        features["volatility_score"]
    )

    # -----------------------------------------
    # DECISION
    # -----------------------------------------

    if confidence >= 80 and risk == "LOW":

        action = "BUY"

    elif confidence >= 60:

        action = "WATCH"

    else:

        action = "AVOID"

    # -----------------------------------------
    # RESULT
    # -----------------------------------------

    return {

        "regime": regime,

        "confidence": confidence,

        "risk": risk,

        "decision": action

    }