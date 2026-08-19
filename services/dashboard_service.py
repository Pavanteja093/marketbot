from services.market_service import (
    get_market_state_data,
    get_direction,
    get_regime,
    get_decision,
)


def get_dashboard_data(symbol="NIFTY"):
    state = get_market_state_data(symbol)

    if state is None:
        return None

    return {
        "state": state,
        "direction": get_direction(symbol)[1],
        "regime": get_regime(symbol)[1],
        "decision": get_decision(symbol)[1],
    }
