import json

from pathlib import Path


MODEL_FILE = (

    Path(__file__).resolve()

    .parent.parent

    / "models"

    / "models.json"

)


def model_scorecard():

    with open(MODEL_FILE) as f:

        models = json.load(f)

    print("\nMODEL SCORECARD")

    print("-" * 40)

    for name, info in models.items():

        print(name)

        print(info)

        print()


if __name__ == "__main__":

    model_scorecard()