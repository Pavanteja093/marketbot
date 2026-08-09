from automation.check_missing_data import missing_days


LOOKBACK_DAYS = 10


def repair_database():

    print("\nChecking previous data...")

    missing_days("stocks_daily")

    missing_days("indices_daily")

    print("\nRepair complete.")


if __name__ == "__main__":

    repair_database()