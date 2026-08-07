from analytics.ranking_engine import build_rankings


def opportunity_report():

    df = build_rankings()

    if df is None:

        return

    strong = df[df["intelligence_score"] >= 80]

    print("\nHIGH CONVICTION OPPORTUNITIES")

    print(strong)


if __name__ == "__main__":

    opportunity_report()