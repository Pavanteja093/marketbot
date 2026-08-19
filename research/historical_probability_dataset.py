from __future__ import annotations

"""MarketBot historical probability dataset adapter.

Research-only adapter for the existing V2 probability forecaster.

Sources:
    factor_history
    market_scenario_history
    forward_returns

The adapter never writes SQLite and never changes the V2 forecaster.
It joins same-date features/scenario state to already-realized forward
returns, then derives the V2-compatible 5-day direction label.
"""

import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "market_intelligence.db"
DEFAULT_ARTIFACT_PATH = (
    BASE_DIR / "research" / "artifacts" / "historical_probability_dataset.csv"
)

UP = "UP"
DOWN = "DOWN"
FLAT = "FLAT"
DEFAULT_FLAT_THRESHOLD_PCT = 0.50

REQUIRED_FACTOR_BASE = {"trade_date", "sector"}
REQUIRED_SCENARIO = {
    "trade_date",
    "primary_scenario",
    "scenario_id",
    "fingerprint",
}
REQUIRED_RETURNS = {
    "trade_date",
    "return_5d",
}

# Keep terminology aligned with v2_probability_forecaster.py.
FACTOR_FEATURE_CANDIDATES = (
    "change_pct",
    "sector_strength",
    "position_pct",
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
)


def classify_return(
    returns: pd.Series,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> pd.Series:
    """Classify realized returns using the existing V2 threshold convention."""
    if flat_threshold_pct < 0:
        raise ValueError("flat_threshold_pct must be >= 0")

    values = pd.to_numeric(returns, errors="coerce")
    labels = pd.Series(index=returns.index, dtype="object")
    labels.loc[values > flat_threshold_pct] = UP
    labels.loc[values < -flat_threshold_pct] = DOWN
    labels.loc[
        values.notna()
        & (values >= -flat_threshold_pct)
        & (values <= flat_threshold_pct)
    ] = FLAT
    return labels


def _resolve_entity_column(columns: Iterable[str], table: str) -> str:
    for candidate in ("index_name", "symbol"):
        if candidate in columns:
            return candidate
    raise ValueError(f"{table} requires index_name or symbol.")


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def _validate_unique(frame: pd.DataFrame, keys: list[str], name: str) -> None:
    dup = frame.duplicated(keys, keep=False)
    if dup.any():
        sample = frame.loc[dup, keys].head(5).to_dict("records")
        raise ValueError(
            f"{name} contains duplicate observations for {keys}: {sample}"
        )


def _prepare_dates(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    out = frame.copy(deep=True)
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    if out["trade_date"].isna().any():
        raise ValueError(f"{name} contains invalid trade_date values.")
    out["trade_date"] = out["trade_date"].dt.normalize()
    return out


def _build_dataset_internal(
    factor_history: pd.DataFrame,
    market_scenario_history: pd.DataFrame,
    forward_returns: pd.DataFrame,
    *,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> pd.DataFrame:
    """Build a deterministic historical probability dataset from DataFrames.

    The feature/scenario date is the prediction date. Forward returns are
    already-realized outcomes indexed by that same prediction date. No row
    may use a scenario from another date.
    """
    factors = _prepare_dates(factor_history, "factor_history")
    scenarios = _prepare_dates(
        market_scenario_history, "market_scenario_history"
    )
    returns = _prepare_dates(forward_returns, "forward_returns")

    _require_columns(factors, REQUIRED_FACTOR_BASE, "factor_history")
    _require_columns(scenarios, REQUIRED_SCENARIO, "market_scenario_history")
    _require_columns(returns, REQUIRED_RETURNS, "forward_returns")

    factor_entity = _resolve_entity_column(factors.columns, "factor_history")
    return_entity = _resolve_entity_column(returns.columns, "forward_returns")

    factors = factors.rename(columns={factor_entity: "index_name"})
    returns = returns.rename(columns={return_entity: "index_name"})

    for frame, name in (
        (factors, "factor_history"),
        (returns, "forward_returns"),
    ):
        frame["index_name"] = frame["index_name"].astype(str).str.strip()
        if (frame["index_name"] == "").any():
            raise ValueError(f"{name} contains blank entity keys.")

    _validate_unique(factors, ["trade_date", "index_name"], "factor_history")
    _validate_unique(returns, ["trade_date", "index_name"], "forward_returns")
    _validate_unique(
        scenarios,
        ["trade_date"],
        "market_scenario_history",
    )

    # Scenario is a market-level state generated for the exact prediction date.
    # Do not forward-fill, backward-fill, or otherwise propagate scenario state.
    scenario_cols = [
        "trade_date",
        "primary_scenario",
        "scenario_id",
        "fingerprint",
    ]
    scenarios = scenarios[scenario_cols].copy()
    scenarios = scenarios.rename(columns={"primary_scenario": "scenario"})

    factor_cols = [
        c 
        for c in FACTOR_FEATURE_CANDIDATES
        if c in factors.columns and factors[c].notna().any()
    ]
    if not factor_cols:
        raise ValueError("factor_history contains no supported factor features.")

    factor_out = factors[
        ["trade_date", "index_name", "sector"] + factor_cols
    ].copy()

    return_out = returns[
        [
            "trade_date",
            "index_name",
            "return_5d",   
        ]
    ].copy()

    merged = factor_out.merge(
        scenarios,
        on="trade_date",
        how="inner",
        validate="many_to_one",
    ).merge(
        return_out,
        on=["trade_date", "index_name"],
        how="inner",
        validate="one_to_one",
    )

    # Only rows with a realized 5-day outcome can receive the target label.
    # Missing auxiliary horizons are excluded rather than fabricated.
    outcome_cols = [
        "return_5d",
    ]
    for col in factor_cols + outcome_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    required_complete = [
    "trade_date",
    "index_name",
    "scenario",
    "scenario_id",
    "fingerprint",
    "return_5d",
    ]
    before = len(merged)
    merged = merged.dropna(subset=required_complete).copy()
    excluded = before - len(merged)
    if before and merged.empty:
        raise ValueError("No complete historical probability rows remain.")

    merged["direction_5d"] = classify_return(
        merged["return_5d"],
        flat_threshold_pct=flat_threshold_pct,
    )

    output_columns = [
        "trade_date",
        "index_name",
        "sector",
        "scenario",
        "scenario_id",
        "fingerprint",
    ] + factor_cols + outcome_cols + ["direction_5d"]

    result = merged[output_columns].copy()
    result["trade_date"] = result["trade_date"].dt.strftime("%Y-%m-%d")

    _validate_unique(
        result,
        ["trade_date", "index_name"],
        "historical_probability_dataset",
    )

    # Deterministic ordering; no source frame is mutated.
    result = result.sort_values(
        ["trade_date", "index_name"],
        kind="mergesort",
    ).reset_index(drop=True)

    return result, excluded


def build_dataset(
    factor_history: pd.DataFrame,
    market_scenario_history: pd.DataFrame,
    forward_returns: pd.DataFrame,
    *,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> pd.DataFrame:
    result, _ = _build_dataset_internal(
        factor_history, market_scenario_history, forward_returns,
        flat_threshold_pct=flat_threshold_pct,
    )
    return result


def build_dataset_with_report(
    factor_history: pd.DataFrame,
    market_scenario_history: pd.DataFrame,
    forward_returns: pd.DataFrame,
    *,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> tuple[pd.DataFrame, int]:
    return _build_dataset_internal(
        factor_history, market_scenario_history, forward_returns,
        flat_threshold_pct=flat_threshold_pct,
    )


def load_source_tables(
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all source tables through SQLite read-only mode."""
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required = {
            "factor_history",
            "market_scenario_history",
            "forward_returns",
        }
        missing = sorted(required - tables)
        if missing:
            raise RuntimeError(
                "Historical probability dataset requires missing tables: "
                + ", ".join(missing)
            )

        factors = pd.read_sql_query(
            "SELECT * FROM factor_history",
            conn,
        )
        scenarios = pd.read_sql_query(
            """
            SELECT trade_date, primary_scenario, scenario_id, fingerprint
            FROM market_scenario_history
            """,
            conn,
        )
        returns = pd.read_sql_query(
            """
            SELECT * FROM forward_returns
            """,
            conn,
        )
    finally:
        conn.close()

    return factors, scenarios, returns


def build_from_database(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> pd.DataFrame:
    factors, scenarios, returns = load_source_tables(db_path)
    return build_dataset(
        factors, scenarios, returns,
        flat_threshold_pct=flat_threshold_pct,
    )


def build_from_database_with_report(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> tuple[pd.DataFrame, int]:
    factors, scenarios, returns = load_source_tables(db_path)
    return build_dataset_with_report(
        factors, scenarios, returns,
        flat_threshold_pct=flat_threshold_pct,
    )


def write_artifact(
    dataset: pd.DataFrame,
    output_path: Path = DEFAULT_ARTIFACT_PATH,
) -> Path:
    """Write only the requested CSV research artifact."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False)
    return output_path


def run(
    db_path: Path = DEFAULT_DB_PATH,
    output_path: Path = DEFAULT_ARTIFACT_PATH,
) -> pd.DataFrame:
    dataset, excluded = build_from_database_with_report(db_path)
    write_artifact(dataset, output_path)

    print("\n" + "=" * 78)
    print("MARKETBOT - HISTORICAL PROBABILITY DATASET")
    print("=" * 78)
    print(f"Rows generated : {len(dataset):,}")
    print(f"Dates          : {dataset['trade_date'].nunique():,}")
    print(f"Symbols        : {dataset['index_name'].nunique():,}")
    print(f"Excluded rows  : {excluded:,}")
    print(
        f"Date range     : {dataset['trade_date'].min()} -> "
        f"{dataset['trade_date'].max()}"
    )
    print("\nDirection 5D")
    print(dataset["direction_5d"].value_counts().reindex(
        [UP, DOWN, FLAT], fill_value=0
    ).to_string())
    print(f"\nSaved: {Path(output_path).resolve()}")
    print("READ-ONLY: SQLite was opened in mode=ro; no production logic changed.")
    return dataset


if __name__ == "__main__":
    run()
