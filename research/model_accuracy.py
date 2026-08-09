import json

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_FILE = BASE_DIR / "models.json"


def update_accuracy(name, accuracy):

    with open(MODEL_FILE, "r") as f:

        models = json.load(f)

    if name in models:

        models[name]["accuracy"] = round(float(accuracy), 4)

    with open(MODEL_FILE, "w") as f:

        json.dump(models, f, indent=4)


if __name__ == "__main__":

    update_accuracy("MarketBot V1", 0.61)