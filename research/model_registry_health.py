import json

from pathlib import Path

MODEL = Path(__file__).resolve().parent.parent / "models.json"


def registry_health():

    with open(MODEL) as f:

        models = json.load(f)

    print("\nMODEL REGISTRY")

    print("-" * 40)

    for model, info in models.items():

        print(model)

        print(info)

        print()


if __name__ == "__main__":

    registry_health()