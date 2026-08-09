"""
MarketBot Feature Engine

Purpose:
--------
Calculates engineered factors for one stock's historical price data.

Used by:
--------
analytics.factor_history_builder

Returns:
--------
{
    "intelligence_score": ...,
    "relative_strength": ...,
    "rs_grade": ...,
    "momentum_score": ...,
    "momentum_grade": ...,
    "trend_score": ...,
    "trend_grade": ...,
    "volatility_score": ...,
    "volatility_grade": ...,
    "liquidity_score": ...,
    "liquidity_grade": ...
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
        market_return
    ):

        # ----------------------------------------------------
        # RELATIVE STRENGTH
        # ----------------------------------------------------

        rs, rs_grade = calculate_relative_strength(
            stock_return,
            market_return
        )

        # ----------------------------------------------------
        # MOMENTUM
        # ----------------------------------------------------

        momentum_score, momentum_grade = calculate_momentum(
            history_df
        )

        # ----------------------------------------------------
        # TREND
        # ----------------------------------------------------

        trend_score, trend_grade = calculate_trend(
            history_df
        )

        # ----------------------------------------------------
        # VOLATILITY
        # ----------------------------------------------------

        volatility_score, volatility_grade = calculate_volatility(
            history_df
        )

        # ----------------------------------------------------
        # LIQUIDITY
        # ----------------------------------------------------

        liquidity_score, liquidity_grade = calculate_liquidity(
            history_df
        )

        # ----------------------------------------------------
        # INTELLIGENCE SCORE
        # ----------------------------------------------------

        intelligence_score = calculate_intelligence(
            {
                "relative_strength": rs,
                "trend_score": trend_score,
                "momentum_score": momentum_score,
                "volatility_score": volatility_score,
                "liquidity_score": liquidity_score
            }
        )

        # ----------------------------------------------------
        # RETURN ALL FACTORS
        # ----------------------------------------------------

        return {

            "intelligence_score":
                intelligence_score,

            "relative_strength":
                rs,

            "rs_grade":
                rs_grade,

            "momentum_score":
                momentum_score,

            "momentum_grade":
                momentum_grade,

            "trend_score":
                trend_score,

            "trend_grade":
                trend_grade,

            "volatility_score":
                volatility_score,

            "volatility_grade":
                volatility_grade,

            "liquidity_score":
                liquidity_score,

            "liquidity_grade":
                liquidity_grade
        }