from datetime import datetime, timedelta


LOOKBACK_DAYS = 15


def repair_window():

    end = datetime.today().date()

    start = end - timedelta(days=LOOKBACK_DAYS)

    print("\nChecking Market Data")

    print(f"{start} -> {end}")

    return start, end


if __name__ == "__main__":

    repair_window()