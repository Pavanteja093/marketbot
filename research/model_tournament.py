import json


def model_tournament():

    with open("models/challengers.json") as f:

        challengers = json.load(f)

    with open("models/model_registry.json") as f:

        registry = json.load(f)

    champion_name = list(registry.keys())[0]

    champion_accuracy = registry[champion_name]["accuracy"]

    print("\nMODEL TOURNAMENT")

    print("-" * 40)

    print("Champion")

    print(champion_name)

    print(champion_accuracy)

    print()

    winner = champion_name

    best = champion_accuracy

    for challenger in challengers:

        print(

            challenger["name"],

            challenger["accuracy"]

        )

        if challenger["accuracy"] > best:

            winner = challenger["name"]

            best = challenger["accuracy"]

    print()

    print("Winner")

    print(winner)