"""
MarketBot Scoring Engine
------------------------

Responsible only for evaluating the current market setup.

Input:
    Market statistics

Output:
    Score
    Bias
    Confidence
    Risk
    Trade Decision
    Strategy
    Reasons
"""


def calculate_trade_score(
    spot,
    support,
    resistance,
    real_pcr,
    avg_iv,
    gamma,
    theta,
    rr
):

    score = 50

    reasons = []

    # ---------------------------------
    # PCR
    # ---------------------------------

    if real_pcr > 1:
        score += 15
        reasons.append("Bullish PCR")
    else:
        score -= 15
        reasons.append("Bearish PCR")

    # ---------------------------------
    # Market Structure
    # ---------------------------------

    distance_support = abs(spot - support)
    distance_resistance = abs(resistance - spot)

    if distance_support < distance_resistance:
        score += 10
        reasons.append("Closer to Support")
    else:
        score -= 20
        reasons.append("Closer to Resistance")

    # ---------------------------------
    # IV
    # ---------------------------------

    if avg_iv > 25:
        score += 10
        reasons.append("High IV")
    else:
        reasons.append("Normal IV")

    # ---------------------------------
    # Gamma
    # ---------------------------------

    if gamma < 0.02:
        score += 5
        reasons.append("Low Gamma")

    # ---------------------------------
    # Theta
    # ---------------------------------

    if theta > 0.5:
        score += 10
        reasons.append("High Theta")

    # ---------------------------------
    # Reward Risk
    # ---------------------------------

    if rr >= 2:
        score += 10
        reasons.append("Excellent Reward/Risk")

    elif rr >= 1:
        score += 5
        reasons.append("Good Reward/Risk")

    else:
        score -= 10
        reasons.append("Poor Reward/Risk")

    score = max(0, min(score, 100))

    # ---------------------------------
    # Bias
    # ---------------------------------

    if score >= 80:

        bias = "BULLISH"
        strategy = "Bull Put Spread"

    elif score >= 65:

        bias = "SLIGHTLY BULLISH"
        strategy = "Iron Condor"

    elif score <= 20:

        bias = "BEARISH"
        strategy = "Bear Call Spread"

    elif score <= 35:

        bias = "SLIGHTLY BEARISH"
        strategy = "Iron Condor"

    else:

        bias = "NEUTRAL"
        strategy = "Wait"

    # ---------------------------------
    # Confidence
    # ---------------------------------

    if bias == "BEARISH":

        confidence = 100 - score

    elif bias == "SLIGHTLY BEARISH":

        confidence = 100 - score

    else:

        confidence = score

    # ---------------------------------
    # Risk
    # ---------------------------------

    if score >= 80:
        risk = "LOW"

    elif score >= 60:
        risk = "MEDIUM"

    else:
        risk = "HIGH"

    # ---------------------------------
    # Trade Decision
    # ---------------------------------

    if score >= 75:

        trade = "YES"

    elif score >= 60:

        if distance_support < distance_resistance:
            trade = "WAIT FOR BOUNCE FROM SUPPORT"
        else:
            trade = "WAIT FOR BREAKOUT ABOVE RESISTANCE"

    else:

        trade = "NO"

    return {

        "score": score,
        "bias": bias,
        "confidence": confidence,
        "risk": risk,
        "trade": trade,
        "strategy": strategy,
        "reasons": reasons

    }