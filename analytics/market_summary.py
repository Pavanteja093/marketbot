from database.repository import Repository


def print_table(title, rows):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    for row in rows:
        if "symbol" in row.keys():
            name = row["symbol"]
        else:
            name = row["index_name"]

        print(f"{name:<15} {row['change_pct']:>8.2f}%")


def market_summary():

    print_table(
        "MARKET SNAPSHOT",
        Repository.latest_indices()
    )

    print_table(
        "TOP GAINERS",
        Repository.top_gainers()
    )

    print_table(
        "TOP LOSERS",
        Repository.top_losers()
    )


if __name__ == "__main__":

    market_summary()