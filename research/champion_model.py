from research.model_registry import (
    get_champion,
    get_model
)


def champion_model():

    champion = get_champion()

    print("\n" + "=" * 60)
    print("MARKETBOT CHAMPION MODEL")
    print("=" * 60)

    if champion is None:

        print("No Champion Model registered.")

        return None

    model = get_model(champion)

    if model is None:

        print(
            f"Champion '{champion}' "
            "is missing from the model registry."
        )

        return None

    print(f"Champion : {champion}")
    print(f"Version  : {model.get('version')}")
    print(f"Accuracy : {model.get('accuracy')}")
    print(f"Status   : {model.get('status')}")

    return model


if __name__ == "__main__":

    champion_model()