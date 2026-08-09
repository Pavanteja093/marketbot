from analytics.intelligence_score_engine import intelligence_score
from analytics.score_normalizer import normalize
from analytics.adaptive_weights import load_weights
from analytics.score_breakdown import score_breakdown


WEIGHTS = load_weights()

def calculate_intelligence(features):

    weights = load_weights()

    intelligence = 0

    for factor, weight in weights.items():

        intelligence += normalize(
            features[factor]
        ) * weight

    return round(intelligence, 2)

    breakdown = score_breakdown(
        features,
        weights
    )

    print("\nFactor Contribution")

    for k, v in breakdown.items():

        print(f"{k:<25} {v:>8}")