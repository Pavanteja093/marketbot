from research.factor_research import factor_research
from learning.learning_statistics import learning_statistics


def research_index():

    print()

    print("=" * 70)
    print("MARKETBOT RESEARCH")
    print("=" * 70)

    learning_statistics()

    factor_research()


if __name__ == "__main__":
    research_index()