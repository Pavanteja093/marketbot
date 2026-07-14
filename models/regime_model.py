from typing import Any

from models.base_model import BaseModel


class RegimeModel(BaseModel):

    name = "Regime Model"

    def predict(self, state) -> dict[str, Any]:

        if state.avg_iv >= 25:

            regime = "HIGH VOLATILITY"

            confidence = 80

            strategy = "IRON CONDOR / SHORT STRANGLE"

        elif state.gamma < 0.002:

            regime = "RANGE BOUND"

            confidence = 70

            strategy = "IRON CONDOR"

        else:

            regime = "TRENDING"

            confidence = 65

            strategy = "DEBIT SPREAD"

        return {

            "regime": regime,

            "confidence": confidence,

            "strategy": strategy

        }