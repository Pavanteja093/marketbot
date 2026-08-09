import json
from pathlib import Path


def model_progress():

    path = Path("models/model_history.json")

    if not path.exists():

        print("\nNo model history found.")
        return

    with open(path) as f:

        history = json.load(f)

    if not history:

        print("\nModel history is empty.")
        return

    print("\n" + "=" * 60)
    print("MODEL EVOLUTION")
    print("=" * 60)

    for model in history:

        print(
            f"{model['version']:15}"
            f" Accuracy : {model['accuracy']:.2%}"
        )