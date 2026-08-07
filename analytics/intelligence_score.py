from analytics.score_normalizer import normalize
from analytics.adaptive_weights import load_weights


WEIGHTS = {

   

}


def calculate_intelligence(features):

    weights = load_weights()

    intelligence = 0

    for factor, weight in weights.items():

        intelligence += normalize(
            features[factor]
        ) * weight

    return round(intelligence, 2)