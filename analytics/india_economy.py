# ----------------------------------
# INDIA ECONOMY
# ----------------------------------

def get_india_economy():

    economy = {

        "cpi_inflation": 4.2,

        "repo_rate": 6.50,

        "bond_yield_10y": 6.75,

        "forex_reserves": 705,

        "trade_deficit": 18
    }

    # ----------------------------------
    # INTERPRETATION
    # ----------------------------------

    if economy["cpi_inflation"] < 5:

        inflation_view = "Under Control"

    else:

        inflation_view = "Elevated"

    if economy["repo_rate"] <= 6.50:

        rate_view = "Neutral"

    else:

        rate_view = "Restrictive"

    economy["inflation_view"] = inflation_view

    economy["rate_view"] = rate_view

    economy["watch_sectors"] = [

        "BANKING",

        "AUTO",

        "CAPITAL GOODS"
    ]

    return economy


# ----------------------------------
# STANDALONE EXECUTION
# ----------------------------------

if __name__ == "__main__":

    economy = get_india_economy()

    print("\n" + "=" * 60)
    print("INDIA ECONOMIC DASHBOARD")
    print("=" * 60)

    print(
        f"\nInflation (CPI) : "
        f"{economy['cpi_inflation']}%"
    )

    print(
        f"Repo Rate       : "
        f"{economy['repo_rate']}%"
    )

    print(
        f"10Y Bond Yield  : "
        f"{economy['bond_yield_10y']}%"
    )

    print(
        f"Forex Reserves  : "
        f"${economy['forex_reserves']} Bn"
    )

    print(
        f"Trade Deficit   : "
        f"${economy['trade_deficit']} Bn"
    )

    print("\nECONOMIC OUTLOOK")
    print("-" * 30)

    print(
        f"Inflation : "
        f"{economy['inflation_view']}"
    )

    print(
        f"Interest Rate Environment : "
        f"{economy['rate_view']}"
    )

    print("\nSECTORS TO WATCH")

    for sector in economy["watch_sectors"]:

        print(f"- {sector}")