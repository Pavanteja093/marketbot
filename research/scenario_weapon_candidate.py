from __future__ import annotations
import pandas as pd

"""
MarketBot Track C - Scenario Weapon Candidate

Small, read-only research module.

Purpose:
    Test a fixed set of standard factor combinations under a small
    number of market scenarios.

Scenarios:
    TREND_UP
    TREND_DOWN
    HIGH_VOL
    LOW_VOL

Weapons:
    TREND_MOMENTUM
    RELATIVE_STRENGTH_TREND
    MOMENTUM_RELATIVE_STRENGTH
    TREND_MOMENTUM_RELATIVE_STRENGTH

This module:
    - reads factor_history and prediction_outcomes
    - derives scenarios from NIFTY daily history
    - performs walk-forward evaluation
    - does not modify the database
    - does not modify production scoring
    - does not modify production weights
    - does not promote candidates
"""

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from research.candidate_gate import evaluate as evaluate_gate


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

FACTORS = [
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

WEAPONS = {
    "TREND_MOMENTUM": [
        "trend_score",
        "momentum_score",
    ],
    "RELATIVE_STRENGTH_TREND": [
        "relative_strength",
        "trend_score",
    ],
    "MOMENTUM_RELATIVE_STRENGTH": [
        "momentum_score",
        "relative_strength",
    ],
    "TREND_MOMENTUM_RELATIVE_STRENGTH": [
        "trend_score",
        "momentum_score",
        "relative_strength",
    ],
}


@dataclass(frozen=True)
class Config:
    train_days: int = 120
    test_days: int = 20
    min_stocks: int = 10


def load_data(db_path: Path = DEFAULT_DB) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(str(db_path))

    try:
        factor = pd.read_sql_query(
            """
            SELECT
                trade_date,
                index_name,
                relative_strength,
                trend_score,
                momentum_score,
                volatility_score,
                liquidity_score
            FROM factor_history
            """,
            conn,
        )

        outcomes = pd.read_sql_query(
            """
            SELECT
                prediction_date,
                index_name,
                return_5d
            FROM prediction_outcomes
            WHERE return_5d IS NOT NULL
            """,
            conn,
        )
    finally:
        conn.close()

    factor["trade_date"] = pd.to_datetime(
        factor["trade_date"], errors="coerce"
    )
    outcomes["prediction_date"] = pd.to_datetime(
        outcomes["prediction_date"], errors="coerce"
    )

    factor["index_name"] = factor["index_name"].astype(str)
    outcomes["index_name"] = outcomes["index_name"].astype(str)

    merged = factor.merge(
        outcomes,
        left_on=["trade_date", "index_name"],
        right_on=["prediction_date", "index_name"],
        how="inner",
    )

    merged = merged.drop(columns=["prediction_date"])

    return merged, load_nifty_scenarios(db_path)


def load_nifty_scenarios(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))

    try:
        cols = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(indices_daily)"
            )
        }

        required = {"trade_date", "symbol", "close"}

        if not required.issubset(cols):
            return pd.DataFrame(columns=["trade_date", "scenario"])

        nifty = pd.read_sql_query(
            """
            SELECT trade_date, close
            FROM indices_daily
            WHERE symbol = 'NIFTY50'
            ORDER BY trade_date
            """,
            conn,
        )
    finally:
        conn.close()

    nifty["trade_date"] = pd.to_datetime(
        nifty["trade_date"], errors="coerce"
    )
    nifty["close"] = pd.to_numeric(nifty["close"], errors="coerce")

    nifty = (
        nifty.dropna(subset=["trade_date", "close"])
        .drop_duplicates("trade_date")
        .sort_values("trade_date")
        .reset_index(drop=True)
    )

    nifty["return_1d"] = nifty["close"].pct_change()
    nifty["vol20"] = nifty["return_1d"].rolling(
        20, min_periods=20
    ).std()

    nifty["sma20"] = nifty["close"].rolling(
        20, min_periods=20
    ).mean()

    nifty["sma50"] = nifty["close"].rolling(
        50, min_periods=50
    ).mean()

    # Expanding thresholds prevent future information leakage.
    nifty["vol_q25"] = (
        nifty["vol20"]
        .expanding(min_periods=60)
        .quantile(0.25)
    )

    nifty["vol_q75"] = (
        nifty["vol20"]
        .expanding(min_periods=60)
        .quantile(0.75)
    )

    scenarios = []

    for _, row in nifty.iterrows():
        close = row["close"]
        sma20 = row["sma20"]
        sma50 = row["sma50"]
        vol = row["vol20"]
        q25 = row["vol_q25"]
        q75 = row["vol_q75"]

        scenario = "UNKNOWN"

        if pd.notna(vol) and pd.notna(q75) and vol >= q75:
            scenario = "HIGH_VOL"

        elif pd.notna(vol) and pd.notna(q25) and vol <= q25:
            scenario = "LOW_VOL"

        elif (
            pd.notna(close)
            and pd.notna(sma20)
            and pd.notna(sma50)
        ):
            if close > sma20 > sma50:
                scenario = "TREND_UP"

            elif close < sma20 < sma50:
                scenario = "TREND_DOWN"

        scenarios.append(scenario)

    nifty["scenario"] = scenarios

    return nifty[["trade_date", "scenario"]]


def normalize_factor_series(
    frame: pd.DataFrame,
    factors: list[str],
) -> pd.DataFrame:
    result = frame.copy()

    for factor in factors:
        result[factor] = pd.to_numeric(
            result[factor],
            errors="coerce",
        )

        median = result[factor].median()

        if not np.isfinite(median):
            median = 0.0

        result[factor] = result[factor].fillna(median)

    return result


def score_weapon(frame, factors):
    clean = normalize_factor_series(frame, factors)

    values = []

    for factor in factors:
        series = clean[factor]
        std = series.std(ddof=0)

        if not np.isfinite(std) or std == 0:
            values.append(pd.Series(0.0, index=clean.index))
        else:
            values.append((series - series.mean()) / std)

    score = sum(values) / len(values)

    return score



def evaluate_day(
    frame: pd.DataFrame,
    factors: list[str],
    min_stocks: int = 10,
) -> dict | None:
    required = set(factors) | {"return_5d", "index_name"}

    if not required.issubset(frame.columns):
        return None

    x = frame.copy()

    x["return_5d"] = pd.to_numeric(
        x["return_5d"],
        errors="coerce",
    )

    x = x.dropna(
        subset=factors + ["return_5d"]
    )

    if len(x) < min_stocks:
        return None

    x["weapon_score"] = score_weapon(x, factors)

    x = x.sort_values(
        ["weapon_score", "index_name"],
        ascending=[False, True],
    )

    n = max(1, len(x) // 5)

    top = x.head(n)["return_5d"].mean()
    bottom = x.tail(n)["return_5d"].mean()

    spread = top - bottom

    return {
        "top_return": float(top),
        "bottom_return": float(bottom),
        "spread": float(spread),
        "observations": int(len(x)),
    }


def run_scenario_walk_forward(
    data: pd.DataFrame,
    scenarios: pd.DataFrame,
    weapon_name: str,
    config: Config = Config(),
) -> pd.DataFrame:
    if weapon_name not in WEAPONS:
        raise ValueError(
            f"Unknown weapon: {weapon_name}"
        )

    factors = WEAPONS[weapon_name]

    x = data.merge(
        scenarios,
        on="trade_date",
        how="inner",
    )

    x = x[
        x["scenario"].isin(
            [
                "TREND_UP",
                "TREND_DOWN",
                "HIGH_VOL",
                "LOW_VOL",
            ]
        )
    ].copy()

    dates = sorted(
        pd.to_datetime(
            x["trade_date"],
            errors="coerce",
        ).dropna().unique()
    )

    if len(dates) < config.train_days + config.test_days:
        return pd.DataFrame()

    results = []

    start = config.train_days

    while start + config.test_days <= len(dates):
        train_dates = dates[
            start - config.train_days : start
        ]

        test_dates = dates[
            start : start + config.test_days
        ]

        # Training data is deliberately used only to establish
        # the historical information boundary. The fixed weapon
        # itself has no fitted parameters.
        train = x[
            x["trade_date"].isin(train_dates)
        ]

        test = x[
            x["trade_date"].isin(test_dates)
        ]

        if train.empty or test.empty:
            start += config.test_days
            continue

        for scenario in [
            "TREND_UP",
            "TREND_DOWN",
            "HIGH_VOL",
            "LOW_VOL",
        ]:
            scenario_test = test[
                test["scenario"] == scenario
            ]

            for date in sorted(
                scenario_test["trade_date"].unique()
            ):
                day = scenario_test[
                    scenario_test["trade_date"] == date
                ]

                evaluation = evaluate_day(
                    day,
                    factors,
                    config.min_stocks,
                )

                if evaluation is None:
                    continue

                results.append(
                    {
                        "weapon": weapon_name,
                        "scenario": scenario,
                        "trade_date": pd.Timestamp(date),
                        **evaluation,
                    }
                )

        start += config.test_days

    return pd.DataFrame(results)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(
            columns=[
                "weapon",
                "scenario",
                "days",
                "mean_spread",
                "median_spread",
                "positive_day_pct",
                "worst_day",
                "best_day",
            ]
        )

    rows = []

    for (weapon, scenario), group in results.groupby(
        ["weapon", "scenario"]
    ):
        spreads = pd.to_numeric(
            group["spread"],
            errors="coerce",
        ).dropna()

        if spreads.empty:
            continue

        rows.append(
            {
                "weapon": weapon,
                "scenario": scenario,
                "days": int(len(spreads)),
                "mean_spread": float(spreads.mean()),
                "median_spread": float(spreads.median()),
                "positive_day_pct": float(
                    (spreads > 0).mean() * 100
                ),
                "worst_day": float(spreads.min()),
                "best_day": float(spreads.max()),
            }
        )

    return pd.DataFrame(rows)


def apply_candidate_gate(
    summary: pd.DataFrame,
) -> pd.DataFrame:
    if summary.empty:
        return summary.copy()

    rows = []

    for _, row in summary.iterrows():
        synthetic = pd.DataFrame(
            {
                "spread": [
                    row["mean_spread"]
                ]
                * int(row["days"])
            }
        )

        gate = evaluate_gate(synthetic)

        rows.append(
            {
                **row.to_dict(),
                "gate_decision": gate["decision"],
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "MarketBot Track C scenario-conditioned "
            "standard weapon research"
        )
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    args = parser.parse_args()

    data, scenarios = load_data(args.db)

    print("=" * 78)
    print("MARKETBOT TRACK C - SCENARIO WEAPON CANDIDATES")
    print("=" * 78)

    print(
        f"Matched observations : {len(data):,}"
    )

    print(
        f"Trading dates        : "
        f"{data['trade_date'].nunique():,}"
    )

    print(
        f"Entities             : "
        f"{data['index_name'].nunique():,}"
    )

    print("\nSCENARIO DISTRIBUTION")

    if scenarios.empty:
        print("No NIFTY scenario data available.")
        return

    print(
        scenarios["scenario"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    all_results = []

    for weapon in WEAPONS:
        result = run_scenario_walk_forward(
            data,
            scenarios,
            weapon,
        )

        if not result.empty:
            all_results.append(result)

    if not all_results:
        print("\nNo evaluable scenario/weapon observations.")
        return

    results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = summarize(results)

    print("\nSCENARIO WEAPON RESULTS")

    print(
        summary.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}",
        )
    )

    print(
        "\nResearch only: "
        "production scoring, weights, challenger logic, "
        "and live trading were NOT changed."
    )


if __name__ == "__main__":
    main()
