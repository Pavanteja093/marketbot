class RecommendationEngine:

    def generate(

        self,

        signal,

        confidence,

        risk

    ):

        recommendation = {

            "signal": signal,

            "confidence": confidence,

            "risk": risk

        }

        if signal == "STRONG BUY":

            recommendation["position_size"] = "Full"

        elif signal == "BUY":

            recommendation["position_size"] = "Half"

        elif signal == "HOLD":

            recommendation["position_size"] = "Watch"

        else:

            recommendation["position_size"] = "Avoid"

        return recommendation

        return {

            "signal": signal,

            "confidence": confidence,

            "risk": risk

        }