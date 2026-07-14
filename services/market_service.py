from database.repository import get_market_state

from models.direction_model import DirectionModel
from models.regime_model import RegimeModel
from models.decision_model import DecisionModel


def get_market_state_data(symbol="NIFTY"):

    return get_market_state(symbol)


def get_direction(symbol="NIFTY"):

    state = get_market_state(symbol)

    if state is None:
        return None

    return state, DirectionModel().predict(state)


def get_regime(symbol="NIFTY"):

    state = get_market_state(symbol)

    if state is None:
        return None

    return state, RegimeModel().predict(state)


def get_decision(symbol="NIFTY"):

    state = get_market_state(symbol)

    if state is None:
        return None

    return state, DecisionModel().predict(state)