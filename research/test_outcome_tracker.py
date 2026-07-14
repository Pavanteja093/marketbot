from learning.outcome_tracker import OutcomeTracker


def main():

    tracker = OutcomeTracker()

    tracker.process_all()

    print("\n" + "=" * 60)
    print("OUTCOME TRACKER")
    print("=" * 60)

    print("\nOutcome Tracker executed successfully.")


if __name__ == "__main__":
    main()