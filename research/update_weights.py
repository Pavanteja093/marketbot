import json

from pathlib import Path

from research.weight_optimizer import optimize_weights


def update_weights():

    weights = optimize_weights()

    path = Path("models/adaptive_weights.json")

    with open(path, "w") as f:

        json.dump(
            weights.to_dict(),
            f,
            indent=4
        )

    print("Adaptive weights updated.")