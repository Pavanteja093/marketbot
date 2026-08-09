import json


def evolution_statistics():

    with open("models/model_registry.json") as f:

        registry = json.load(f)

    print("\nMODEL EVOLUTION")

    print("-" * 50)

    for name, model in registry.items():

        print()

        print(name)

        print("Version :", model["version"])

        print("Wins    :", model["wins"])

        print("Losses  :", model["losses"])

        print("Accuracy:", model["accuracy"])