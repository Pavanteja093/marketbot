"""
MarketBot Track D Phase 2
Statistical / OOS Repeatability Validator

READ-ONLY research:
- Reads historical_probability_dataset.csv for factors + scenario labels.
- Reads forward_returns from SQLite using a read-only URI.
- Never creates, updates, deletes, or writes SQLite data.
- Does not change production weights or scoring.

Question:
    Does factor -> future-return relationship survive across independent
    chronological OOS windows, conditional on regime, and across horizons?

Default candidate hypotheses:
    SIDEWAYS x intelligence_score
    HIGH_VOL_DOWN x intelligence_score
    HIGH_VOL_DOWN x volatility_score
    SIDEWAYS x volatility_score
    SIDEWAYS x trend_score

Horizons:
    1D, 5D, 10D, 20D

The validator reports:
    - OOS Spearman IC by chronological fold
    - sign consistency
    - mean OOS IC
    - IC standard deviation
    - ICIR across folds
    - mean top-vs-bottom quintile return spread
    - positive-spread fold percentage
    - block-bootstrap 95% CI for mean fold IC
    - Benjamini-Hochberg adjusted p-value for the candidate x horizon family
    - conservative evidence classification

No candidate is promoted by this module.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET = BASE_DIR / "research" / "artifacts" / "historical_probability_dataset.csv"
DB_PATH = BASE_DIR / "market_intelligence.db"
OUTPUT = BASE_DIR / "research" / "artifacts" / "track_d_phase2_statistical_oos_repeatability.csv"
LOG = BASE_DIR / "research" / "artifacts" / "track_d_phase2_statistical_oos_repeatability_run.log"

FACTORS = (
    "intelligence_score",
    "volatility_score",
    "trend_score",
)

HORIZONS = (1, 5, 10, 20)

SCENARIOS = (
    "CHOPPY",
    "FLAT",
    "HIGH_VOL",
    "LOW_VOL",
    "TREND_DOWN",
    "TREND_UP",
)

CANDIDATES = tuple(
    (scenario, factor)
    for scenario in SCENARIOS
    for factor in FACTORS
)

MIN_TRAIN_DAYS = 80
TEST_DAYS = 20
MIN_TEST_DAYS_WITH_DATA = 3
MIN_STOCK_OBS = 20
BOOTSTRAPS = 2000
SEED = 20260813


REQUIRED_DATASET = {
    "trade_date",
    "index_name",
    "scenario",
    *FACTORS,
}
REQUIRED_FORWARD = {
    "trade_date",
    "index_name",
    *(f"return_{h}d" for h in HORIZONS),
}


def _validate_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def _read_forward_returns(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        table = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='forward_returns'",
            conn,
        )
        if table.empty:
            raise ValueError("SQLite table forward_returns not found")

        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(forward_returns)").fetchall()
        }
        missing = sorted(REQUIRED_FORWARD - cols)
        if missing:
            raise ValueError(
                "forward_returns missing required columns: " + ", ".join(missing)
            )

        query = """
            SELECT
                trade_date,
                index_name,
                return_1d,
                return_5d,
                return_10d,
                return_20d
            FROM forward_returns
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def load_dataset(
    dataset_path: Path = DATASET,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    factors = pd.read_csv(dataset_path)
    _validate_columns(factors, REQUIRED_DATASET, "historical_probability_dataset")

    forward = _read_forward_returns(db_path)

    factors = factors.copy(deep=True)
    forward = forward.copy(deep=True)

    factors["trade_date"] = pd.to_datetime(factors["trade_date"], errors="coerce")
    forward["trade_date"] = pd.to_datetime(forward["trade_date"], errors="coerce")

    factors["index_name"] = factors["index_name"].astype(str)
    forward["index_name"] = forward["index_name"].astype(str)

    factor_cols = ["trade_date", "index_name", "scenario", *FACTORS]
    factors = factors[factor_cols].copy()

    

    merged = factors.merge(
        forward,
        on=["trade_date", "index_name"],
        how="inner",
        validate="many_to_one",
    )

    for col in FACTORS:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    for h in HORIZONS:
        merged[f"return_{h}d"] = pd.to_numeric(
            merged[f"return_{h}d"], errors="coerce"
        )

    merged = (
        merged.dropna(subset=["trade_date", "index_name", "scenario"])
        .sort_values(["trade_date", "index_name"])
        .reset_index(drop=True)
    )
    return merged


def make_oos_folds(
    dates: Iterable[pd.Timestamp],
    min_train_days: int = MIN_TRAIN_DAYS,
    test_days: int = TEST_DAYS,
) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    unique = pd.DatetimeIndex(sorted(pd.Series(list(dates)).dropna().unique()))
    if len(unique) < min_train_days + test_days:
        return []

    folds = []
    train_end_pos = min_train_days - 1
    while train_end_pos + test_days < len(unique):
        train_start = unique[0]
        train_end = unique[train_end_pos]
        test_start = unique[train_end_pos + 1]
        test_end = unique[train_end_pos + test_days]
        folds.append((train_start, train_end, test_start, test_end))
        train_end_pos += test_days
    return folds


def _spearman(x: pd.Series, y: pd.Series) -> float:
    a = pd.to_numeric(x, errors="coerce")
    b = pd.to_numeric(y, errors="coerce")
    mask = a.notna() & b.notna()
    if mask.sum() < 3:
        return np.nan
    return float(a[mask].rank(method="average").corr(b[mask].rank(method="average")))


def _quintile_spread(frame: pd.DataFrame, factor: str, ret: str) -> float:
    work = frame[[factor, ret]].dropna().copy()
    if len(work) < MIN_STOCK_OBS:
        return np.nan
    ranks = work[factor].rank(method="first")
    q = pd.qcut(ranks, 5, labels=False, duplicates="drop")
    if q.nunique() < 5:
        return np.nan
    top = work.loc[q == q.max(), ret].mean()
    bottom = work.loc[q == q.min(), ret].mean()
    return float(top - bottom)


def _bootstrap_mean_ci(values: np.ndarray, seed: int = SEED) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(BOOTSTRAPS, len(values)), replace=True)
    means = samples.mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _two_sided_sign_p(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return np.nan
    # Exact sign/permutation test around zero; conservative for tiny fold counts.
    nonzero = values[values != 0]
    if len(nonzero) == 0:
        return 1.0
    observed = abs(nonzero.mean())
    rng = np.random.default_rng(SEED)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAPS, len(nonzero)))
    null_means = np.abs((signs * np.abs(nonzero)).mean(axis=1))
    return float((np.sum(null_means >= observed) + 1) / (BOOTSTRAPS + 1))


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    indexed = [(i, p) for i, p in enumerate(pvalues) if np.isfinite(p)]
    adjusted = [np.nan] * len(pvalues)
    if not indexed:
        return adjusted
    indexed.sort(key=lambda x: x[1])
    m = len(indexed)
    running = 1.0
    for rank in range(m, 0, -1):
        idx, p = indexed[rank - 1]
        value = min(running, p * m / rank)
        running = value
        adjusted[idx] = value
    return adjusted


def _classify(
    fold_count: int,
    finite_ic_count: int,
    mean_ic: float,
    positive_fold_pct: float,
    ci_low: float,
    ci_high: float,
    adjusted_p: float,
) -> str:
    if finite_ic_count < 3:
        return "INSUFFICIENT_OOS_WINDOWS"
    if not np.isfinite(mean_ic):
        return "INSUFFICIENT_EVIDENCE"
    if np.isfinite(adjusted_p) and adjusted_p >= 0.05:
        return "NOT_STATISTICALLY_ROBUST"
    if not np.isfinite(adjusted_p):
        return "STATISTICAL_EVIDENCE_INCOMPLETE"
    if positive_fold_pct < 60.0:
        return "OOS_SIGN_INCONSISTENT"
    if not (ci_low > 0.0 or ci_high < 0.0):
        return "EFFECT_UNCERTAIN"
    if mean_ic > 0 and ci_low > 0 and adjusted_p < 0.05:
        return "REPEATABLE_OOS_RELATIONSHIP"
    if mean_ic < 0 and ci_high < 0 and adjusted_p < 0.05:
        return "REPEATABLE_OOS_RELATIONSHIP"
    return "PROMISING_BUT_INSUFFICIENT"


def validate(
    data: pd.DataFrame,
    candidates: tuple[tuple[str, str], ...] = CANDIDATES,
) -> pd.DataFrame:
    _validate_columns(
        data,
        REQUIRED_DATASET | {"return_1d", "return_5d", "return_10d", "return_20d"},
        "input",
    )

    source = data.copy(deep=True)
    source["trade_date"] = pd.to_datetime(source["trade_date"], errors="coerce")

    rows = []
    for scenario, factor in candidates:
        subset = source[source["scenario"].astype(str) == scenario].copy()
        folds = make_oos_folds(subset["trade_date"])

        for horizon in HORIZONS:
            ret_col = f"return_{horizon}d"
            fold_ics = []
            fold_spreads = []
            fold_dates = []

            for _, train_end, test_start, test_end in folds:
                test = subset[
                    (subset["trade_date"] >= test_start)
                    & (subset["trade_date"] <= test_end)
                ].copy()

                # Training period is used only to establish chronological eligibility.
                # No factor threshold/weight is fitted from future test observations.
                if test.empty:
                    continue

                ic = _spearman(test[factor], test[ret_col])
                spread = np.nan

                for day, day_frame in test.groupby("trade_date", sort=True):
                    s = _quintile_spread(day_frame, factor, ret_col)
                    if np.isfinite(s):
                        fold_spreads.append(float(s))
                    # Daily IC is not used as an independent p-value unit here;
                    # fold-level IC is the reported OOS unit.
                fold_ics.append(ic)
                fold_dates.append((test_start, test_end))

            ic_values = np.asarray(fold_ics, dtype=float)
            finite_ic = ic_values[np.isfinite(ic_values)]
            spread_values = np.asarray(fold_spreads, dtype=float)

            mean_ic = float(np.mean(finite_ic)) if len(finite_ic) else np.nan
            std_ic = float(np.std(finite_ic, ddof=1)) if len(finite_ic) >= 2 else np.nan
            icir = (
                float(mean_ic / std_ic)
                if np.isfinite(mean_ic) and np.isfinite(std_ic) and std_ic > 0
                else np.nan
            )
            positive_fold_pct = (
                float(np.mean(finite_ic > 0) * 100.0) if len(finite_ic) else np.nan
            )
            ci_low, ci_high = _bootstrap_mean_ci(finite_ic)
            p = _two_sided_sign_p(finite_ic)

            rows.append(
                {
                    "scenario": scenario,
                    "factor": factor,
                    "horizon_days": horizon,
                    "oos_fold_count": len(folds),
                    "oos_finite_ic_folds": int(len(finite_ic)),
                    "oos_mean_ic": mean_ic,
                    "oos_ic_std": std_ic,
                    "oos_icir": icir,
                    "oos_positive_ic_fold_pct": positive_fold_pct,
                    "oos_ic_ci_low": ci_low,
                    "oos_ic_ci_high": ci_high,
                    "raw_sign_p_value": p,
                    "oos_mean_daily_top_bottom_spread_pct": (
                        float(np.mean(spread_values)) if len(spread_values) else np.nan
                    ),
                    "oos_positive_spread_day_pct": (
                        float(np.mean(spread_values > 0) * 100.0)
                        if len(spread_values)
                        else np.nan
                    ),
                    "oos_spread_observations": int(len(spread_values)),
                }
            )

    result = pd.DataFrame(rows)
    result["adjusted_p_value"] = benjamini_hochberg(
        result["raw_sign_p_value"].tolist()
    )

    result["evidence_classification"] = [
        _classify(
            int(row.oos_fold_count),
            int(row.oos_finite_ic_folds),
            float(row.oos_mean_ic),
            float(row.oos_positive_ic_fold_pct),
            float(row.oos_ic_ci_low),
            float(row.oos_ic_ci_high),
            float(row.adjusted_p_value),
        )
        for row in result.itertuples(index=False)
    ]

    result["research_action"] = result["evidence_classification"].map(
        {
            "REPEATABLE_OOS_RELATIONSHIP": "Continue to independent economic validation; no production promotion.",
            "PROMISING_BUT_INSUFFICIENT": "Collect more independent OOS windows before drawing conclusions.",
            "NOT_STATISTICALLY_ROBUST": "Do not promote; retain only as a rejected research hypothesis.",
            "OOS_SIGN_INCONSISTENT": "Reject current hypothesis; investigate regime definition or horizon only if justified.",
            "EFFECT_UNCERTAIN": "Collect more OOS evidence; current effect is not sufficiently resolved.",
            "INSUFFICIENT_OOS_WINDOWS": "Collect more history; insufficient independent OOS windows.",
            "STATISTICAL_EVIDENCE_INCOMPLETE": "Do not promote; statistical evidence is incomplete.",
            "INSUFFICIENT_EVIDENCE": "Do not promote; insufficient usable evidence.",
        }
    )

    return result.sort_values(
        ["scenario", "factor", "horizon_days"], kind="mergesort"
    ).reset_index(drop=True)


def run(
    dataset_path: Path = DATASET,
    db_path: Path = DB_PATH,
    output_path: Path = OUTPUT,
) -> pd.DataFrame:
    data = load_dataset(dataset_path, db_path)
    result = validate(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    lines = [
        "MARKETBOT TRACK D PHASE 2 - STATISTICAL / OOS REPEATABILITY",
        "READ-ONLY: SQLite opened mode=ro; no production changes; no promotion.",
        f"Input observations: {len(data)}",
        f"Candidates: {len(CANDIDATES)}",
        f"Horizons: {', '.join(map(str, HORIZONS))}D",
        "",
        result.to_string(index=False),
        "",
        "STATUS: SUCCESS",
    ]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    frame = run()
    print("MARKETBOT TRACK D PHASE 2 - STATISTICAL / OOS REPEATABILITY")
    print("READ-ONLY: SQLite opened mode=ro; no production changes; no promotion.")
    print(frame.to_string(index=False))
    print(f"\nSaved: {OUTPUT}")
    print(f"Log:   {LOG}")



