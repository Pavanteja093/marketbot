def top_opportunities(rankings):

    return rankings[
        rankings["intelligence_score"] >= 70
    ].sort_values(
        "intelligence_score",
        ascending=False
    )