import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def calculate_oi_levels(df: pd.DataFrame) -> dict:
    """
    Calculate OI-derived support and resistance.

    Contract
    --------
    Support:
        Highest Put OI at or below spot.

    Resistance:
        Highest Call OI at or above spot.

    This prevents a high-OI strike on the wrong side of spot
    from being classified as support/resistance.
    """

    required = {
        "strike",
        "call_oi",
        "put_oi",
        "spot_price",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"OI calculation missing required columns: "
            f"{sorted(missing)}"
        )

    clean = df.copy()

    for column in [
        "strike",
        "call_oi",
        "put_oi",
        "spot_price",
    ]:
        clean[column] = pd.to_numeric(
            clean[column],
            errors="coerce",
        )

    clean = clean.dropna(
        subset=[
            "strike",
            "call_oi",
            "put_oi",
            "spot_price",
        ]
    )

    if clean.empty:
        raise ValueError(
            "OI calculation received no valid option rows."
        )

    spot = float(clean["spot_price"].iloc[0])

    support_candidates = clean[
        clean["strike"] <= spot
    ]

    resistance_candidates = clean[
        clean["strike"] >= spot
    ]

    if support_candidates.empty:
        raise ValueError(
            f"No valid support strike at or below spot "
            f"{spot:.2f}"
        )

    if resistance_candidates.empty:
        raise ValueError(
            f"No valid resistance strike at or above spot "
            f"{spot:.2f}"
        )

    support_row = support_candidates.loc[
        support_candidates["put_oi"].idxmax()
    ]

    resistance_row = resistance_candidates.loc[
        resistance_candidates["call_oi"].idxmax()
    ]

    support = float(support_row["strike"])
    resistance = float(resistance_row["strike"])

    if support > spot:
        raise AssertionError(
            f"OI contract violation: support {support} "
            f"is above spot {spot}"
        )

    if resistance < spot:
        raise AssertionError(
            f"OI contract violation: resistance {resistance} "
            f"is below spot {spot}"
        )

    return {
        "spot_price": spot,
        "support": support,
        "resistance": resistance,
        "support_put_oi": float(
            support_row["put_oi"]
        ),
        "resistance_call_oi": float(
            resistance_row["call_oi"]
        ),
        "range_width": resistance - support,
    }


def load_latest_option_data() -> pd.DataFrame:

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT *
        FROM option_chain_history o
        WHERE trade_time = (
            SELECT MAX(trade_time)
            FROM option_chain_history
            WHERE symbol = o.symbol
        )
    """

    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def run_oi_analysis() -> None:

    df = load_latest_option_data()

    if df.empty:
        raise RuntimeError(
            "OI engine found no latest option-chain data."
        )

    print()
    print("=" * 60)
    print("OI ANALYSIS")
    print("=" * 60)

    failures = []

    for symbol in sorted(df["symbol"].dropna().unique()):

        temp = df[df["symbol"] == symbol].copy()

        print()
        print("=" * 60)
        print(symbol)
        print("=" * 60)

        try:
            result = calculate_oi_levels(temp)

            print(
                f"Spot Price        : "
                f"{result['spot_price']:.2f}"
            )

            print()
            print("RESISTANCE")
            print(
                f"Strike            : "
                f"{int(result['resistance'])}"
            )
            print(
                f"Call OI           : "
                f"{result['resistance_call_oi']:,.0f}"
            )

            print()
            print("SUPPORT")
            print(
                f"Strike            : "
                f"{int(result['support'])}"
            )
            print(
                f"Put OI            : "
                f"{result['support_put_oi']:,.0f}"
            )

            print()
            print(
                f"Range_width       : "
                f"{int(result['range_width'])}"
            )

            print()
            print("CONTRACT           : PASS")

        except Exception as exc:

            failures.append(
                f"{symbol}: {type(exc).__name__}: {exc}"
            )

            print()
            print("CONTRACT           : FAIL")
            print(f"ERROR              : {exc}")

    print()
    print("=" * 60)
    print("OI ENGINE SUMMARY")
    print("=" * 60)

    if failures:
        print("STATUS             : FAIL")

        for failure in failures:
            print(f"FAIL               : {failure}")

        raise RuntimeError(
            "OI engine calculation contract failed."
        )

    print("STATUS             : PASS")
    print("All OI support/resistance calculations are valid.")


if __name__ == "__main__":
    run_oi_analysis()
