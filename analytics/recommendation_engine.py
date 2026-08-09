class RecommendationEngine:

    def generate(

        self,

        signal,

        confidence,

        risk,

        expected_return=0,

        position_size="Auto"

    ):

        recommendation = {

            "signal": signal,

            "confidence": confidence,

            "risk": risk,

            "expected_return": expected_return,

            "position_size": position_size

        }

        if signal == "STRONG BUY":

            recommendation["action"] = "BUY NOW"

            recommendation["priority"] = 1

        elif signal == "BUY":

            recommendation["action"] = "BUY"

            recommendation["priority"] = 2

        elif signal == "HOLD":

            recommendation["action"] = "WATCH"

            recommendation["priority"] = 3

        else:

            recommendation["action"] = "AVOID"

            recommendation["priority"] = 4

        return recommendation