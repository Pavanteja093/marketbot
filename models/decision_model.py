from typing import Any

from models.base_model import BaseModel
from models.direction_model import DirectionModel
from models.regime_model import RegimeModel


class DecisionModel(BaseModel):

    name = "Decision Model"

    def predict(self, state) -> dict[str, Any]:

        direction = DirectionModel().predict(state)

        regime = RegimeModel().predict(state)

        trade = direction["trade"]

        strategy = direction["strategy"]

        confidence = round(
            (direction["confidence"] + regime["confidence"]) / 2
        )

        return {

            "prediction": direction["prediction"],

            "regime": regime["regime"],

            "trade": trade,
            
            "score": confidence,

            "strategy": strategy,

            "confidence": confidence,

            "risk": direction["risk"],

            "reasons": direction["reasons"]

        }