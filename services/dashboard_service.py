from database.repository import get_market_state

from models.direction_model import DirectionModel
from models.regime_model import RegimeModel
from models.decision_model import DecisionModel


def get_dashboard_data(symbol="NIFTY"):

    state = get_market_state(symbol)

    if state is None:
        return None

    direction = DirectionModel().predict(state)

    regime = RegimeModel().predict(state)

    decision = DecisionModel().predict(state)

    return {
        "state": state,
        "direction": direction,
        "regime": regime,
        "decision": decision,
    }