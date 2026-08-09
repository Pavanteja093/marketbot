from analytics.feature_engine import build_features
from analytics.market_regime import detect_regime
from analytics.confidence_engine import confidence_score
from analytics.risk_engine import calculate_risk
from analytics.intelligence_score_engine import intelligence_score


def build_intelligence(option_data):

    # -----------------------------------------
    # 1. BUILD BASE FEATURES
    # -----------------------------------------

    features = build_features(option_data)

    # -----------------------------------------
    # 2. INTELLIGENCE SCORE
    # -----------------------------------------

    features["intelligence_score"] = intelligence_score(
        features
    )

    # -----------------------------------------
    # 3. MARKET REGIME
    # -----------------------------------------

    features["regime"] = detect_regime(
        features
    )

    # -----------------------------------------
    # 4. CONFIDENCE
    # -----------------------------------------

    features["confidence"] = confidence_score(
        features
    )

    # -----------------------------------------
    # 5. RISK
    # -----------------------------------------

    features["risk"] = calculate_risk(
        features["volatility_score"]
    )

    # -----------------------------------------
    # FINAL INTELLIGENCE OBJECT
    # -----------------------------------------

    return features