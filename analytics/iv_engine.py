from database.repository import (
    get_latest_option_chain,
    save_iv_analysis
)


SYMBOLS = [
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY"
]


def analyze_iv(symbol):

    df = get_latest_option_chain(symbol)

    if df.empty:
        return None

    avg_call_iv = round(df["call_iv"].mean(), 2)
    avg_put_iv = round(df["put_iv"].mean(), 2)

    avg_iv = round(
        (avg_call_iv + avg_put_iv) / 2,
        2
    )

    if avg_iv < 15:

        regime = "LOW VOLATILITY"

        strategy = (
            "BUY OPTIONS / "
            "LONG STRADDLE / "
            "DEBIT SPREAD"
        )

    elif avg_iv < 25:

        regime = "NORMAL VOLATILITY"

        strategy = (
            "DIRECTIONAL TRADES / "
            "BULL PUT SPREAD / "
            "BEAR CALL SPREAD"
        )

    else:

        regime = "HIGH VOLATILITY"

        strategy = (
            "IRON CONDOR / "
            "SHORT STRANGLE / "
            "CREDIT SPREAD"
        )

    trade_time = df.iloc[0]["trade_time"]

    save_iv_analysis(
        trade_time,
        symbol,
        avg_call_iv,
        avg_put_iv,
        avg_iv,
        regime,
        strategy
    )

    return {

        "trade_time": trade_time,

        "symbol": symbol,

        "avg_call_iv": avg_call_iv,

        "avg_put_iv": avg_put_iv,

        "avg_iv": avg_iv,

        "regime": regime,

        "strategy": strategy

    }


def run_iv_engine():

    print("\n" + "=" * 60)
    print("IV ANALYSIS")
    print("=" * 60)

    results = []

    for symbol in SYMBOLS:

        result = analyze_iv(symbol)

        if result is None:
            continue

        results.append(result)

        print("\n" + "=" * 60)
        print(result["symbol"])
        print("=" * 60)

        print(f"Average Call IV : {result['avg_call_iv']}")
        print(f"Average Put IV  : {result['avg_put_iv']}")
        print(f"Average IV      : {result['avg_iv']}")

        print("\nIV REGIME")
        print(result["regime"])

        print("\nRECOMMENDED")
        print(result["strategy"])

    return results


if __name__ == "__main__":
    run_iv_engine()