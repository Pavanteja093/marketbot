from research.model_registry import (
    load_models,
    save_models,
    get_champion
)


MIN_IMPROVEMENT = 0.02


def promote_model(
    accuracy,
    version
):

    models = load_models()

    champion = get_champion()

    if champion is None:

        models[version] = {

            "version": version,

            "accuracy": accuracy,

            "status": "Champion"

        }

        save_models(models)

        print(
            f"Model {version} promoted as Champion"
        )

        return True

    champion_accuracy = models[
        champion
    ].get(
        "accuracy",
        0.0
    )

    improvement = (
        accuracy -
        champion_accuracy
    )

    print("\n" + "=" * 60)
    print("MODEL PROMOTION")
    print("=" * 60)

    print(
        f"Champion         : {champion}"
    )

    print(
        f"Champion Accuracy: {champion_accuracy:.4f}"
    )

    print(
        f"Challenger       : {version}"
    )

    print(
        f"Challenger Accuracy: {accuracy:.4f}"
    )

    print(
        f"Improvement      : {improvement:.4f}"
    )

    if improvement < MIN_IMPROVEMENT:

        print(
            "PROMOTION REJECTED"
        )

        print(
            f"Required improvement: "
            f"{MIN_IMPROVEMENT:.4f}"
        )

        return False

    models[version] = {

        "version": version,

        "accuracy": accuracy,

        "status": "Champion"

    }

    models[champion]["status"] = "Retired"

    save_models(models)

    print(
        "NEW CHAMPION MODEL PROMOTED"
    )

    return True


if __name__ == "__main__":

    print(
        "Promotion module loaded."
    )