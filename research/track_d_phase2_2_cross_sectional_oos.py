from __future__ import annotations

import sqlite3
from math import comb
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET = BASE_DIR / "research/artifacts/historical_probability_dataset.csv"
DB_PATH = BASE_DIR / "market_intelligence.db"
OUTPUT = BASE_DIR / "research/artifacts/track_d_phase2_2_cross_sectional_oos.csv"
RUN_LOG = BASE_DIR / "research/artifacts/track_d_phase2_2_cross_sectional_oos_run.log"

FACTORS = (
    "intelligence_score",
    "trend_score",
    "volatility_score",
    "relative_strength",
    "momentum_score",
    "change_pct",
    "liquidity_score",
)
REGIMES = ("TREND_UP", "TREND_DOWN", "HIGH_VOL", "LOW_VOL", "FLAT", "CHOPPY")
HORIZONS = (1, 5, 10, 20)

# Match Track D Phase 2.1 chronology/gating exactly.
MIN_TRAIN_DAYS = 80
TEST_DAYS = 20
MIN_IC_OBS = 3
MIN_CROSS_SECTIONAL_OBS = 10
BOOTSTRAPS = 2000
SEED = 20260813

REQ_DATA = {"trade_date", "index_name", "scenario", *FACTORS}
REQ_FWD = {"trade_date", "index_name", *(f"return_{h}d" for h in HORIZONS)}


def validate_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def read_forward_returns(db_path: Path = DB_PATH) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(forward_returns)").fetchall()}
        if not cols:
            raise ValueError("SQLite table forward_returns not found")
        missing = sorted(REQ_FWD - cols)
        if missing:
            raise ValueError(
                "forward_returns missing required columns: " + ", ".join(missing)
            )
        return pd.read_sql_query(
            "SELECT trade_date,index_name,return_1d,return_5d,return_10d,return_20d "
            "FROM forward_returns",
            conn,
        )
    finally:
        conn.close()


def load_dataset(
    dataset_path: Path = DATASET, db_path: Path = DB_PATH
) -> pd.DataFrame:
    factors = pd.read_csv(dataset_path)
    validate_columns(factors, REQ_DATA, "historical_probability_dataset")
    forward = read_forward_returns(db_path)

    factors = factors.copy(deep=True)
    forward = forward.copy(deep=True)
    factors["trade_date"] = pd.to_datetime(factors["trade_date"], errors="coerce")
    forward["trade_date"] = pd.to_datetime(forward["trade_date"], errors="coerce")
    factors["index_name"] = factors["index_name"].astype(str).str.strip()
    forward["index_name"] = forward["index_name"].astype(str).str.strip()

    factors = factors[["trade_date", "index_name", "scenario", *FACTORS]]
    forward = forward[
        ["trade_date", "index_name", *[f"return_{h}d" for h in HORIZONS]]
    ]

    # The research dataset and forward_returns should each contain one row per
    # date/symbol. Enforce the requested one-to-one join rather than silently
    # multiplying observations.
    if factors.duplicated(["trade_date", "index_name"]).any():
        raise ValueError("historical_probability_dataset has duplicate date/index rows")
    if forward.duplicated(["trade_date", "index_name"]).any():
        raise ValueError("forward_returns has duplicate date/index rows")

    out = factors.merge(
        forward,
        on=["trade_date", "index_name"],
        how="inner",
        validate="one_to_one",
    )
    out["scenario"] = out["scenario"].astype(str).str.strip()
    for c in FACTORS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for h in HORIZONS:
        out[f"return_{h}d"] = pd.to_numeric(out[f"return_{h}d"], errors="coerce")

    out = out.dropna(subset=["trade_date", "index_name", "scenario"])
    out = out[out["scenario"].isin(REGIMES)].copy()
    return out.sort_values(["trade_date", "index_name"], kind="mergesort").reset_index(drop=True)


def make_global_oos_folds(
    dates: Iterable[pd.Timestamp],
    min_train_days: int = MIN_TRAIN_DAYS,
    test_days: int = TEST_DAYS,
) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    if min_train_days < 1 or test_days < 1:
        raise ValueError("fold parameters must be positive")
    unique = pd.DatetimeIndex(sorted(pd.Series(list(dates)).dropna().unique()))
    if len(unique) < min_train_days + test_days:
        return []
    folds = []
    p = min_train_days - 1
    while p + test_days < len(unique):
        folds.append((unique[0], unique[p], unique[p + 1], unique[p + test_days]))
        p += test_days
    return folds


def cross_sectional_rank(frame: pd.DataFrame, factor: str) -> pd.Series:
    """Rank a factor only against stocks on the same trading date."""
    if factor not in frame.columns or "trade_date" not in frame.columns:
        raise ValueError("frame must contain trade_date and the requested factor")
    values = pd.to_numeric(frame[factor], errors="coerce")
    return values.groupby(frame["trade_date"], sort=False).rank(method="average", pct=True)


def _daily_cross_sectional_stats(
    day: pd.DataFrame, factor: str, return_col: str
) -> tuple[float, float, float, int]:
    work = day[["trade_date", "index_name", factor, return_col]].copy(deep=True)
    work[factor] = pd.to_numeric(work[factor], errors="coerce")
    work[return_col] = pd.to_numeric(work[return_col], errors="coerce")
    work = work.dropna(subset=[factor, return_col])
    if len(work) < MIN_CROSS_SECTIONAL_OBS:
        return np.nan, np.nan, np.nan, len(work)

    x = work[factor]
    y = work[return_col]
    if x.nunique() < 2 or y.nunique() < 2:
        return np.nan, np.nan, np.nan, len(work)

    ic = float(x.rank(method="average").corr(y.rank(method="average")))
    q = x.rank(method="average", pct=True)
    # Exact cross-sectional quintile membership. For ties, ranking produces a
    # stable fractional ordering without using any other date's information.
    bottom = y[q <= 0.2]
    top = y[q > 0.8]
    if bottom.empty or top.empty:
        return ic, np.nan, np.nan, len(work)
    spread = float(top.mean() - bottom.mean())
    return ic, float(top.mean()), float(bottom.mean()), len(work)


def _sign_test_pvalue(values: Sequence[float]) -> float:
    a = [float(v) for v in values if pd.notna(v) and float(v) != 0]
    if not a:
        return np.nan
    n = len(a)
    k = sum(v > 0 for v in a)
    if k >= n / 2:
        tail = sum(comb(n, i) for i in range(k, n + 1))
    else:
        tail = sum(comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2.0 * tail / (2**n))


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    values = np.asarray(list(p_values), dtype=float)
    out = np.full(len(values), np.nan)
    finite = np.flatnonzero(np.isfinite(values))
    if len(finite) == 0:
        return out.tolist()
    order = finite[np.argsort(values[finite], kind="mergesort")]
    m = len(order)
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, values[i] * m / rank)
        out[i] = min(1.0, running)
    return out.tolist()


def bootstrap_mean_ci(
    values: Sequence[float], seed: int = SEED, n_bootstrap: int = BOOTSTRAPS
) -> tuple[float, float]:
    a = np.asarray([float(v) for v in values if pd.notna(v)], dtype=float)
    if len(a) == 0:
        return np.nan, np.nan
    if len(a) == 1:
        return float(a[0]), float(a[0])
    rng = np.random.default_rng(seed)
    samples = rng.choice(a, size=(n_bootstrap, len(a)), replace=True).mean(axis=1)
    return float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def _classify(
    oos_folds: int,
    finite_ic_folds: int,
    positive_ic_pct: float,
    positive_spread_pct: float,
    adjusted_p: float,
    ci_low: float,
    ci_high: float,
) -> str:
    if oos_folds == 0 or finite_ic_folds == 0:
        return "NO_DATA"
    if oos_folds < 2 or finite_ic_folds < 2:
        return "TEMPORALLY_INADEQUATE"
    if not np.isfinite(adjusted_p):
        return "UNVALIDATED"
    if positive_ic_pct <= 25 or positive_spread_pct <= 25:
        return "NEGATIVE"
    if (
        positive_ic_pct >= 75
        and positive_spread_pct >= 75
        and adjusted_p < 0.05
        and np.isfinite(ci_low)
        and ci_low > 0
    ):
        return "PRELIMINARY_SIGNAL"
    if adjusted_p < 0.05 or (np.isfinite(ci_low) and np.isfinite(ci_high) and ci_low <= 0 <= ci_high):
        return "WEAK_INCONSISTENT"
    return "UNVALIDATED"


def validate(
    data: pd.DataFrame,
    regimes: Sequence[str] = REGIMES,
    factors: Sequence[str] = FACTORS,
    horizons: Sequence[int] = HORIZONS,
    min_train_days: int = MIN_TRAIN_DAYS,
    test_days: int = TEST_DAYS,
) -> pd.DataFrame:
    required = {"trade_date", "index_name", "scenario", *factors}
    required |= {f"return_{h}d" for h in horizons}
    validate_columns(data, required, "cross_sectional_oos_dataset")

    original = data.copy(deep=True)
    w = original.copy(deep=True)
    w["trade_date"] = pd.to_datetime(w["trade_date"], errors="coerce")
    w["scenario"] = w["scenario"].astype(str)
    for c in factors:
        w[c] = pd.to_numeric(w[c], errors="coerce")
    for h in horizons:
        w[f"return_{h}d"] = pd.to_numeric(w[f"return_{h}d"], errors="coerce")

    folds = make_global_oos_folds(w["trade_date"].dropna().unique(), min_train_days, test_days)
    rows: list[dict] = []

    for regime in regimes:
        regime_data = w[w["scenario"].eq(regime)].copy()
        regime_dates = pd.DatetimeIndex(regime_data["trade_date"].dropna().unique())
        oos_dates: set[pd.Timestamp] = set()

        for _, _, test_start, test_end in folds:
            oos_dates.update(regime_dates[(regime_dates >= test_start) & (regime_dates <= test_end)])

        for factor in factors:
            for horizon in horizons:
                return_col = f"return_{horizon}d"
                fold_ics: list[float] = []
                fold_spreads: list[float] = []
                top_returns: list[float] = []
                bottom_returns: list[float] = []
                fold_counts = 0
                date_counts = 0
                stock_counts: list[int] = []

                for _, (_, _, test_start, test_end) in enumerate(folds, 1):
                    test = regime_data[
                        (regime_data["trade_date"] >= test_start)
                        & (regime_data["trade_date"] <= test_end)
                    ].copy()
                    if test.empty:
                        continue
                    fold_counts += 1

                    daily_ics: list[float] = []
                    daily_spreads: list[float] = []
                    daily_top: list[float] = []
                    daily_bottom: list[float] = []
                    for _, day in test.groupby("trade_date", sort=True):
                        ic, top, bottom, n = _daily_cross_sectional_stats(day, factor, return_col)
                        stock_counts.append(n)
                        if n >= MIN_CROSS_SECTIONAL_OBS:
                            date_counts += 1
                        if pd.notna(ic):
                            daily_ics.append(float(ic))
                        if pd.notna(top) and pd.notna(bottom):
                            daily_top.append(float(top))
                            daily_bottom.append(float(bottom))
                            daily_spreads.append(float(top - bottom))

                    # Each OOS fold contributes one observation to the fold-level
                    # statistics, using only its chronological test dates.
                    if daily_ics:
                        fold_ics.append(float(np.mean(daily_ics)))
                    if daily_spreads:
                        fold_spreads.append(float(np.mean(daily_spreads)))
                        top_returns.append(float(np.mean(daily_top)))
                        bottom_returns.append(float(np.mean(daily_bottom)))

                ia = np.asarray(fold_ics, dtype=float)
                sa = np.asarray(fold_spreads, dtype=float)
                mean_ic = float(ia.mean()) if len(ia) else np.nan
                ic_std = float(ia.std(ddof=1)) if len(ia) > 1 else np.nan
                icir = (
                    float(mean_ic / ic_std)
                    if np.isfinite(mean_ic) and np.isfinite(ic_std) and ic_std > 0
                    else np.nan
                )
                positive_ic_pct = float((ia > 0).mean() * 100) if len(ia) else np.nan
                mean_spread = float(sa.mean()) if len(sa) else np.nan
                positive_spread_pct = float((sa > 0).mean() * 100) if len(sa) else np.nan
                ci_low, ci_high = bootstrap_mean_ci(sa)
                raw_p = _sign_test_pvalue(sa)
                rows.append(
                    {
                        "scenario": regime,
                        "factor": factor,
                        "horizon_days": horizon,
                        "global_oos_fold_count": len(folds),
                        "oos_fold_count": fold_counts,
                        "oos_finite_ic_folds": len(ia),
                        "regime_total_dates": len(regime_dates),
                        "regime_oos_dates": len(oos_dates),
                        "oos_usable_dates": date_counts,
                        "mean_stocks_per_date": float(np.mean(stock_counts)) if stock_counts else np.nan,
                        "oos_mean_ic": mean_ic,
                        "oos_ic_std": ic_std,
                        "oos_icir": icir,
                        "oos_positive_ic_fold_pct": positive_ic_pct,
                        "mean_top_quintile_return": float(np.mean(top_returns)) if top_returns else np.nan,
                        "mean_bottom_quintile_return": float(np.mean(bottom_returns)) if bottom_returns else np.nan,
                        "mean_quintile_spread": mean_spread,
                        "positive_spread_fold_pct": positive_spread_pct,
                        "bootstrap_95ci_low": ci_low,
                        "bootstrap_95ci_high": ci_high,
                        "raw_sign_test_p_value": raw_p,
                        "adjusted_p_value": np.nan,
                        "evidence_classification": "PENDING_BH",
                    }
                )

    out = pd.DataFrame(rows)
    # One clearly defined family: all scenario × factor × horizon tests.
    out["adjusted_p_value"] = benjamini_hochberg(out["raw_sign_test_p_value"].tolist())
    out["evidence_classification"] = [
        _classify(
            int(r.oos_fold_count),
            int(r.oos_finite_ic_folds),
            float(r.oos_positive_ic_fold_pct) if pd.notna(r.oos_positive_ic_fold_pct) else np.nan,
            float(r.positive_spread_fold_pct) if pd.notna(r.positive_spread_fold_pct) else np.nan,
            float(r.adjusted_p_value) if pd.notna(r.adjusted_p_value) else np.nan,
            float(r.bootstrap_95ci_low) if pd.notna(r.bootstrap_95ci_low) else np.nan,
            float(r.bootstrap_95ci_high) if pd.notna(r.bootstrap_95ci_high) else np.nan,
        )
        for r in out.itertuples()
    ]
    out = out.sort_values(["scenario", "factor", "horizon_days"], kind="mergesort").reset_index(drop=True)
    pd.testing.assert_frame_equal(data, original)
    return out


def run(
    dataset_path: Path = DATASET,
    db_path: Path = DB_PATH,
    output_path: Path = OUTPUT,
    run_log: Path = RUN_LOG,
) -> pd.DataFrame:
    data = load_dataset(dataset_path, db_path)
    result = validate(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, lineterminator="\n")

    lines = [
        "MARKETBOT TRACK D PHASE 2.2 - CROSS-SECTIONAL FACTOR OOS VALIDATION",
        "READ-ONLY",
        "SQLite writes: NONE",
        "Production changes: NONE",
        "Factor-weight changes: NONE",
        "Candidate promotion: NONE",
        f"Input observations: {len(data)}",
        f"Trading dates: {data['trade_date'].nunique()}",
        f"Symbols: {data['index_name'].nunique()}",
        f"Rows written: {len(result)}",
        f"CSV: {output_path}",
        "",
        result.to_string(index=False),
    ]
    run_log.parent.mkdir(parents=True, exist_ok=True)
    run_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return result


if __name__ == "__main__":
    run()
