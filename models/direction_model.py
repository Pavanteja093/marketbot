from models.base_model import BaseModel
from analytics.scoring_engine import calculate_trade_score


class DirectionModel(BaseModel):

    name = "Direction Model"

    def predict(self, state):

        result = calculate_trade_score(
            spot=state.spot_price,
            support=state.support,
            resistance=state.resistance,
            real_pcr=state.pcr,
            avg_iv=state.avg_iv,
            gamma=state.gamma,
            theta=state.theta,
            rr=state.reward_risk
        )

        score = result["score"]

        # ---------------------------------
        # Direction Probabilities
        # ---------------------------------

        bullish = min(95, max(5, score))

        bearish = min(95, max(5, 100 - score))

        neutral = max(
            5,
            100 - abs(bullish - bearish)
        )

        # Normalize

        total = bullish + bearish + neutral

        bullish = round(bullish * 100 / total)

        bearish = round(bearish * 100 / total)

        neutral = 100 - bullish - bearish

        return {

            "prediction": result["bias"],

            "bias": result["bias"],

            "confidence": result["confidence"],

            "score": result["score"],

            "risk": result["risk"],

            "trade": result["trade"],

            "strategy": result["strategy"],

            "reasons": result["reasons"],

            "bullish_probability": bullish,

            "bearish_probability": bearish,

            "neutral_probability": neutral

        }