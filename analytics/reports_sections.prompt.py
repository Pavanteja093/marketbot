def print_section(title):

    print("\n")
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_dataframe(df):

    print(df.to_string(index=False))