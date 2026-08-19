from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

ARTIFACT_DIR = BASE_DIR / "res  earch" / "artifacts"
DEFAULT_OUTPUT = ARTIFACT_DIR / "scenario_factor_conditional_evidence.csv"

FACTORS = [
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

REQUIRED_COLUMNS = {
    "trade_date",
    "index_name",
    "primary_scenario",
    "scenario_id",
    "fingerprint",
    *FACTORS,
    "return_5d",
}


def load_data(db_path=DB_PATH) -> pd.DataFrame:
    query = """
    SELECT
        f.trade_date,
        f.index_name,
        s.primary_scenario,
        s.scenario_id,
        s.fingerprint,
        f.intelligence_score,
        f.relative_strength,
        f.trend_score,
        f.momentum_score,
        f.volatility_score,
        f.liquidity_score,
        fr.return_5d
    FROM factor_history f
    INNER JOIN market_scenario_history s
        ON DATE(f.trade_date) = DATE(s.trade_date)
    INNER JOIN forward_returns fr
        ON DATE(fr.trade_date) = DATE(f.trade_date)
       AND fr.index_name = f.index_name
    WHERE fr.return_5d IS NOT NULL
    ORDER BY
        f.trade_date,
        f.index_name,
        s.scenario_id
    """

    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(
            "Conditional evidence input is missing required columns: "
            + ", ".join(missing)
        )


def _factor_state(value: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if value < 40:
        return "LOW"
    if value < 60:
        return "MEDIUM"
    if value < 80:
        return "HIGH"
    return "VERY_HIGH"


def build_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    validate_input(frame)

    rows = []

    for scenario, factor_name in (
        (scenario, factor)
        for scenario in sorted(frame["primary_scenario"].dropna().unique())
        for factor in FACTORS
    ):
        subset = frame[
            (frame["primary_scenario"] == scenario)
            & frame[factor_name].notna()
            & frame["return_5d"].notna()
        ].copy()

        if subset.empty:
            continue

        subset["factor_state"] = subset[factor_name].map(_factor_state)

        for state in ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]:
            state_df = subset[subset["factor_state"] == state]

            if state_df.empty:
                continue

            returns = state_df["return_5d"].astype(float)

            rows.append(
                {
                    "primary_scenario": scenario,
                    "factor": factor_name,
                    "factor_state": state,
                    "observations": int(len(state_df)),
                    "scenario_dates": int(
                        state_df["trade_date"].nunique()
                    ),
                    "symbols": int(
                        state_df["index_name"].nunique()
                    ),
                    "positive_5d_pct": float(
                        (returns > 0).mean() * 100.0
                    ),
                    "mean_return_5d": float(returns.mean()),
                    "median_return_5d": float(returns.median()),
                    "worst_return_5d": float(returns.min()),
                    "best_return_5d": float(returns.max()),
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        return pd.DataFrame(
            columns=[
                "primary_scenario",
                "factor",
                "factor_state",
                "observations",
                "scenario_dates",
                "symbols",
                "positive_5d_pct",
                "mean_return_5d",
                "median_return_5d",
                "worst_return_5d",
                "best_return_5d",
            ]
        )

    return result.sort_values(
        [
            "primary_scenario",
            "factor",
            "factor_state",
        ],
        kind="mergesort",
    ).reset_index(drop=True)


def run(
    db_path=DB_PATH,
    output_path=DEFAULT_OUTPUT,
) -> pd.DataFrame:
    frame = load_data(db_path)
    result = build_evidence(frame)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    return result


def main() -> None:
    frame = load_data(DB_PATH)

    print("=" * 80)
    print("MARKETBOT - SCENARIO × FACTOR CONDITIONAL EVIDENCE")
    print("=" * 80)

    if frame.empty:
        print("\nINSUFFICIENT DATA")
        print("No factor/scenario observations have completed 5-day outcomes.")
        return

    print(f"\nStock observations : {len(frame)}")
    print(f"Scenario dates     : {frame['trade_date'].nunique()}")
    print(f"Scenarios          : {frame['primary_scenario'].nunique()}")
    print(f"Symbols            : {frame['index_name'].nunique()}")

    result = build_evidence(frame)

    print(f"Evidence rows      : {len(result)}")

    print("\nTOP CONDITIONAL RELATIONSHIPS")

    if not result.empty:
        display = result.sort_values(
            ["positive_5d_pct", "observations"],
            ascending=[False, False],
        ).head(15)

        print(
            display[
                [
                    "primary_scenario",
                    "factor",
                    "factor_state",
                    "observations",
                    "scenario_dates",
                    "positive_5d_pct",
                    "mean_return_5d",
                    "median_return_5d",
                ]
            ].to_string(index=False)
        )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(DEFAULT_OUTPUT, index=False)

    print(f"\nSaved: {DEFAULT_OUTPUT}")
    print(
        "\nREAD-ONLY: no SQLite writes, production scoring changes, "
        "factor-weight changes, candidate promotion, or trading changes."
    )


if __name__ == "__main__":
    main()
