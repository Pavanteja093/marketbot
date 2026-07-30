from database.repository import Repository


class IntelligenceEngine:

    @staticmethod
    def evaluate(symbol):

        state = Repository.market_state(symbol)

        return {

            "symbol": state.symbol,

            "bias": state.market_bias,

            "confidence": state.confidence,

            "strategy": state.recommended_strategy,

            "expected_move": state.expected_move,

            "reward_risk": state.reward_risk,

            "trade_quality": state.trade_quality,

            "market_location": state.market_location,

            "support": state.support,

            "resistance": state.resistance,

            "max_pain": state.max_pain,

            "summary": (
                f"{state.market_bias} market "
                f"with {state.confidence:.0f}% confidence. "
                f"Preferred strategy: {state.recommended_strategy}."
            )

        }