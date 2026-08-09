import json
from pathlib import Path


def generate_challenger():

    registry = Path("models/model_registry.json")
    challengers = Path("models/challengers.json")

    with open(registry) as f:
        champion = json.load(f)

    champion_name = list(champion.keys())[0]

    version = champion[champion_name]["version"]

    challenger = {

        "name": f"MarketBot Challenger {version}",

        "accuracy": 0,

        "status": "Testing"

    }

    if challengers.exists():

        with open(challengers) as f:

            data = json.load(f)

    else:

        data = []

    data.append(challenger)

    with open(challengers, "w") as f:

        json.dump(data, f, indent=4)

    print("New Challenger Created")