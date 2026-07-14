from database.repository import get_market_state

from database.learning_repository import save_market_prediction

from models.decision_model import DecisionModel

def save_market_prediction_history():

    symbols = [
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY"
    ]

    model = DecisionModel()

    for symbol in symbols:

        state = get_market_state(symbol)

        if state is None:
            continue

        decision = model.predict(state)

        record = {

    "trade_time": state.trade_time,

    "symbol": state.symbol,

    "prediction": decision["prediction"],

    "confidence": decision["confidence"],

    "strategy": decision["strategy"],

    "trade": decision["trade"],

    "risk": decision["risk"],

    "score": decision["score"],

    "support": state.support,

    "resistance": state.resistance,

    "spot_price": state.spot_price,

    "pcr": state.pcr,

    "avg_iv": state.avg_iv

        }
    
        save_market_prediction(record)

if __name__ == "__main__":

    save_market_prediction_history()

    print("\nMarket Prediction History Saved Successfully")