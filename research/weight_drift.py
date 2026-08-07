import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

WEIGHT_FILE = BASE_DIR / "weights.json"


def weight_drift():

    with open(WEIGHT_FILE) as f:

        weights = json.load(f)

    print("\nHighest Weight")

    winner = max(weights, key=weights.get)

    print(winner, ":", weights[winner])

    print("\nLowest Weight")

    loser = min(weights, key=weights.get)

    print(loser, ":", weights[loser])


if __name__ == "__main__":
    weight_drift()