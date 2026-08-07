"""
MarketBot Feature Engine

Purpose:
--------
Calculates all engineered features for one stock.

Returns:
--------
{
    "relative_strength": ...,
    "rs_grade": ...,
    "momentum_score": ...,
    "momentum_grade": ...,
    "trend_score": ...,
    "trend_grade": ...
}
"""

from analytics.relative_strength import calculate_relative_strength
from analytics.momentum_score import calculate_momentum
from analytics.trend_score import calculate_trend
from analytics.volatility_score import calculate_volatility
from analytics.liquidity_score import calculate_liquidity
from analytics.intelligence_score import calculate_intelligence


class FeatureEngine:

    def build_features(
        self,
        history_df,
        stock_return,
        market_returns
    ):

        rs, rs_grade = calculate_relative_strength(
            stock_return,
            market_returns
        )

        momentum_score, momentum_grade = calculate_momentum(
            history_df
        )

        trend_score, trend_grade = calculate_trend(
            history_df
        )

        volatility_score, volatility_grade = calculate_volatility(
            history_df
        )

        liquidity_score, liquidity_grade = calculate_liquidity(
            history_df
        )
        intelligence_score = calculate_intelligence({

        "relative_strength": rs,

        "trend_score": trend_score,

        "momentum_score": momentum_score,

        "volatility_score": volatility_score,

        "liquidity_score": liquidity_score

        })

        features =  {

            "intelligence_score": intelligence_score,

            "relative_strength": rs,
            "rs_grade": rs_grade,

            "momentum_score": momentum_score,
            "momentum_grade": momentum_grade,

            "trend_score": trend_score,
            "trend_grade": trend_grade,

            "volatility_score": volatility_score,
            "volatility_grade": volatility_grade,

            "liquidity_score": liquidity_score,
            "liquidity_grade": liquidity_grade

        }

        return features