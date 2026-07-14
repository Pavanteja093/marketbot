from database.learning_repository import (
    get_pending_predictions,
    get_next_index_close,
    save_learning_record,
    mark_prediction_processed
)

class OutcomeTracker:

    def __init__(self):
        pass

    def calculate_return(self, spot_price, next_close):

        if spot_price is None or next_close is None:
            return None

        if spot_price == 0:
            return None

        return ((next_close - spot_price) / spot_price) * 100
    
    def classify_market_move(self, market_return):

        if market_return is None:
            return "UNKNOWN"

        if market_return >= 0.50:
            return "BULLISH"

        elif market_return <= -0.50:
            return "BEARISH"

        else:
            return "NEUTRAL"


    def evaluate_prediction(self, prediction, actual):

        return prediction == actual
    
    def build_learning_record(
        self,
        trade_date,
        symbol,
        prediction,
        actual,
        confidence,
        strategy,
        trade_quality,
        spot_price,
        next_close,
        next_day_return
    ):

        return {

            "trade_date": trade_date,

            "symbol": symbol,

            "prediction": prediction,

            "actual_outcome": actual,

            "confidence": confidence,

            "strategy": strategy,

            "trade_quality": trade_quality,

            "spot_price": spot_price,

            "next_close": next_close,

            "next_day_return": next_day_return,

            # We'll calculate this later
            "five_day_return": None,

            "correct": prediction == actual

        }



    def process_prediction(self, prediction):

        print("\n-----------------------------------")
        print(f"Processing : {prediction['symbol']}")

        next_day = get_next_index_close(

            prediction["symbol"],
            prediction["trade_time"]

        )

        if next_day is None:

            print("Next day data not available.")

            return

        market_return = self.calculate_return(

            prediction["spot_price"],
            next_day["close"]

        )

        actual = self.classify_market_move(
            market_return
        )

        correct = self.evaluate_prediction(

            prediction["prediction"],
            actual

        )

        record = self.build_learning_record(

            prediction=prediction["prediction"],

            actual=actual,

            confidence=prediction["confidence"],

            strategy=prediction["strategy"],

            trade_quality=prediction["score"],

            spot_price=prediction["spot_price"],

            next_close=next_day["close"],

            trade_date=prediction["trade_time"],

            symbol=prediction["symbol"],

            next_day_return=market_return

        )
        print("\nLearning Record")

        for key, value in record.items():

            print(f"{key:20} : {value}")

        save_learning_record(record)

        mark_prediction_processed(
            prediction["id"]
        )


    def process_all(self):

        predictions = get_pending_predictions()

        print("\n" + "=" * 60)
        print("OUTCOME TRACKER")
        print("=" * 60)

        print(f"\nPending Predictions : {len(predictions)}")

        for prediction in predictions:

            self.process_prediction(prediction)

