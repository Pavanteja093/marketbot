import pandas as pd


class ModelValidator:

    def validate(self, predictions):

        total = len(predictions)

        if total == 0:

            return {

                "accuracy": 0,

                "total": 0

            }

        correct = (
            predictions["predicted_direction"] ==
            predictions["actual_direction"]
        ).sum()

        accuracy = correct / total * 100

        return {

            "accuracy":
                round(
                    accuracy,
                    2
                ),

            "total":
                total

        }