from learning.similarity_engine import SimilarityEngine


class ConfidenceCalibration:

    def __init__(self):

        self.engine = SimilarityEngine()

    def calibrate(
        self,
        intelligence_score,
        sector_strength,
        position_pct
    ):

        data = self.engine.similar_market(
            intelligence_score,
            sector_strength,
            position_pct
        )

        stats = self.engine.statistics(data)

        if stats is None:
        
            return None

        if stats["observations"] < 30:

            return {

                "confidence": None,

                "confidence_level": "INSUFFICIENT DATA",

                "observations": stats["observations"]

            }

        win_rate = stats["win_rate"]

        if win_rate >= 80:
            level = "VERY HIGH"

        elif win_rate >= 70:
            level = "HIGH"

        elif win_rate >= 55:
            level = "MEDIUM"

        elif win_rate >= 40:
            level = "LOW"

        else:
            level = "VERY LOW"

        return {

            "confidence": win_rate,

            "confidence_level": level,

            "observations": stats["observations"],

            "average_return": stats["average_return"],

            "median_return": stats["median_return"],

            "volatility": stats["volatility"]

        }


def demo():

    model = ConfidenceCalibration()

    result = model.calibrate(

        intelligence_score=80,

        sector_strength=2,

        position_pct=80

    )

    print("\n==============================")

    print("CONFIDENCE CALIBRATION")

    print("==============================")

    print(result)


if __name__ == "__main__":

    demo()