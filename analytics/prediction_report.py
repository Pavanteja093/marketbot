from analytics.prediction_engine_v2 import predict


def print_prediction(history_df,
                     intelligence_score,
                     volatility_score):

    result = predict(
        history_df,
        intelligence_score,
        volatility_score
    )

    print()

    print("=" * 60)
    print("AI PREDICTION")
    print("=" * 60)

    for key, value in result.items():

        print(f"{key:<20} {value}")