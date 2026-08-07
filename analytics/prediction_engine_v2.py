from analytics.expected_return import expected_return
from analytics.win_probability import calculate_win_probability

from analytics.confidence_engine import confidence_score
from analytics.signal_generator import generate_signal
from analytics.risk_engine import calculate_risk
from analytics.position_sizing import suggested_position


def predict(history_df, intelligence_score, volatility_score):

    expected = expected_return(history_df)

    probability = calculate_win_probability(
        history_df
    )

    confidence = confidence_score(
        probability,
        intelligence_score
    )

    signal = generate_signal(
        confidence
    )

    risk = calculate_risk(
        volatility_score
    )

    position = suggested_position(
        confidence
    )

    return {

        "expected_return": expected,

        "win_probability": probability,

        "confidence": confidence,

        "signal": signal,

        "risk": risk,

        "position_size": position
    }