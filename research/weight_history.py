import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

WEIGHT_FILE = BASE_DIR / "weights.json"


def weight_history():

    with open(WEIGHT_FILE) as f:

        weights = json.load(f)

    print("\nCurrent Learned Weights")
    print("-" * 40)

    for factor, value in weights.items():

        print(f"{factor:<25} {value:.3f}")


if __name__ == "__main__":
    weight_history()