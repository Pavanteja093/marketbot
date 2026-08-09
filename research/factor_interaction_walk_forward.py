from __future__ import annotations

import itertools
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

FACTORS = [
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

# C3.2 survivors. These are frozen research candidates; this module does
# not discover new interactions and does not modify production scoring.
CANDIDATES = [
    ("relative_strength", "trend_score"),
    ("trend_score", "momentum_score"),
]

# Same broad walk-forward geometry used by the existing MarketBot research:
# 120 trading days of training followed by 20 trading days of testing,
# advanced by one test window.
TRAIN_DAYS = 120
TEST_DAYS = 20
MIN_ENTITIES_PER_DAY = 5


def _resolve_entity_column(conn: sqlite3.Connection, table: str) -> str:
    columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }

    if "index_name" in columns:
        return "index_name"
    if "symbol" in columns:
        return "symbol"

    raise RuntimeError(
        f"{table} has neither index_name nor symbol. "
        "Cannot resolve the cross-sectional entity."
    )


def load_data(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Load factor/outcome observations using the existing MarketBot schema."""
    conn = sqlite3.connect(str(db_path))

    try:
        factor_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(factor_history)").fetchall()
        }
        outcome_cols = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(prediction_outcomes)"
            ).fetchall()
        }

        missing = [factor for factor in FACTORS if factor not in factor_cols]
        if missing:
            raise RuntimeError(
                f"factor_history missing factors required by C3.3: {missing}"
            )

        if "return_5d" not in outcome_cols:
            raise RuntimeError("prediction_outcomes missing return_5d.")

        factor_entity = _resolve_entity_column(conn, "factor_history")
        outcome_entity = _resolve_entity_column(conn, "prediction_outcomes")

        query = f"""
            SELECT
                DATE(f.trade_date) AS trade_date,
                f.{factor_entity} AS entity,
                {", ".join(f"f.{factor}" for factor in FACTORS)},
                o.intelligence_score AS production_score,
                o.return_5d
            FROM factor_history AS f
            INNER JOIN prediction_outcomes AS o
                ON DATE(f.trade_date) = DATE(o.prediction_date)
               AND f.{factor_entity} = o.{outcome_entity}
            WHERE
                o.return_5d IS NOT NULL
                AND o.intelligence_score IS NOT NULL
            ORDER BY DATE(f.trade_date), f.{factor_entity}
        """

        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")

    for column in FACTORS + ["production_score", "return_5d"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return (
        df.dropna(
            subset=FACTORS + ["production_score", "return_5d", "trade_date"]
        )
        .sort_values(["trade_date", "entity"])
        .reset_index(drop=True)
    )


def _rank_cross_section(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:
    return frame.groupby("trade_date", sort=False)[column].rank(
        method="average",
        pct=True,
    )


def _build_interaction(
    frame: pd.DataFrame,
    left: str,
    right: str,
) -> pd.Series:
    left_rank = _rank_cross_section(frame, left)
    right_rank = _rank_cross_section(frame, right)

    # Centered rank interaction. This is the same construction used by C3.1.
    return (left_rank - 0.5) * (right_rank - 0.5)


def _daily_spearman(
    group: pd.DataFrame,
    score_column: str,
) -> float:
    x = pd.to_numeric(group[score_column], errors="coerce")
    y = pd.to_numeric(group["return_5d"], errors="coerce")

    valid = x.notna() & y.notna()

    if valid.sum() < MIN_ENTITIES_PER_DAY:
        return np.nan

    if x[valid].nunique() < 2 or y[valid].nunique() < 2:
        return np.nan

    return float(x[valid].corr(y[valid], method="spearman"))


def _daily_top_bottom(
    group: pd.DataFrame,
    score_column: str,
) -> tuple[float, float, float, float, int]:
    work = group[[score_column, "return_5d"]].dropna().copy()

    if len(work) < MIN_ENTITIES_PER_DAY:
        return np.nan, np.nan, np.nan, np.nan, 0

    # Rank first so tied scores cannot create duplicate qcut edges.
    ranks = work[score_column].rank(method="first")
    quintile = pd.qcut(ranks, 5, labels=False)

    top = work.loc[quintile == 4, "return_5d"]
    bottom = work.loc[quintile == 0, "return_5d"]

    if top.empty or bottom.empty:
        return np.nan, np.nan, np.nan, np.nan, 0

    top_mean = float(top.mean())
    bottom_mean = float(bottom.mean())
    spread = top_mean - bottom_mean
    top_win = float((top > 0).mean() * 100)
    bottom_win = float((bottom > 0).mean() * 100)

    return top_mean, bottom_mean, spread, top_win, int(len(work))


def _normalise_weights(ic: pd.Series) -> pd.Series:
    """
    Convert signed training ICs into stable research weights.

    Direction is retained separately. Magnitudes determine the allocation.
    A tiny floor avoids a factor disappearing solely because its sample IC is
    close to zero.
    """
    magnitude = ic.abs().fillna(0.0)
    if magnitude.sum() <= 0:
        return pd.Series(1.0 / len(ic), index=ic.index)

    return magnitude / magnitude.sum()


def _train_factor_model(train: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Leakage-safe training model.

    Uses only TRAIN observations to estimate factor directions and magnitude
    weights. The TEST set is never consulted here.
    """
    daily_ic = {}

    for factor in FACTORS:
        values = (
            train.groupby("trade_date", sort=True)
            .apply(
                lambda g: _daily_spearman(g, factor),
                include_groups=False,
            )
            .dropna()
        )
        daily_ic[factor] = float(values.mean()) if not values.empty else 0.0

    ic = pd.Series(daily_ic, dtype=float)
    directions = pd.Series(
        np.where(ic >= 0, 1.0, -1.0),
        index=ic.index,
        dtype=float,
    )
    weights = _normalise_weights(ic)

    return directions, weights


def _build_baseline_score(
    frame: pd.DataFrame,
    directions: pd.Series,
    weights: pd.Series,
) -> pd.Series:
    """Build a cross-sectional rank-normalized research baseline."""
    score = pd.Series(0.0, index=frame.index)

    for factor in FACTORS:
        rank = _rank_cross_section(frame, factor)
        signed_rank = (rank - 0.5) * directions[factor]
        score += signed_rank * weights[factor]

    return score


def _build_candidate_score(
    frame: pd.DataFrame,
    directions: pd.Series,
    weights: pd.Series,
    left: str,
    right: str,
) -> pd.Series:
    """
    Candidate = baseline + one interaction term.

    Interaction magnitude is scaled to the average absolute factor weight so
    that the experiment measures incremental value rather than allowing an
    unbounded interaction to dominate the baseline.
    """
    baseline = _build_baseline_score(frame, directions, weights)
    interaction = _build_interaction(frame, left, right)

    interaction_ic = _daily_spearman(
        pd.DataFrame(
            {
                "interaction": interaction,
                "return_5d": frame["return_5d"],
                "trade_date": frame["trade_date"],
            }
        ),
        "interaction",
    )

    # IMPORTANT: this helper is only called on TRAIN when fitting. For TEST,
    # caller supplies a frozen interaction coefficient.
    if pd.isna(interaction_ic):
        interaction_ic = 0.0

    coefficient = float(interaction_ic) * 0.5

    return baseline + interaction * coefficient


def _fit_interaction_coefficient(
    train: pd.DataFrame,
    left: str,
    right: str,
) -> float:
    interaction = _build_interaction(train, left, right)

    work = train[
        ["trade_date", "return_5d"]
    ].copy()
    work["interaction"] = interaction

    daily = (
        work.groupby("trade_date", sort=True)
        .apply(
            lambda g: _daily_spearman(g, "interaction"),
            include_groups=False,
        )
        .dropna()
    )

    mean_ic = float(daily.mean()) if not daily.empty else 0.0

    # Conservative shrinkage. C3.3 is measuring incremental usefulness,
    # not trying to maximize in-sample performance.
    return mean_ic * 0.5


def _build_candidate_score_frozen(
    frame: pd.DataFrame,
    directions: pd.Series,
    weights: pd.Series,
    left: str,
    right: str,
    coefficient: float,
) -> pd.Series:
    baseline = _build_baseline_score(frame, directions, weights)
    interaction = _build_interaction(frame, left, right)

    return baseline + interaction * coefficient


def _evaluate_period(
    frame: pd.DataFrame,
    score_column: str,
) -> dict:
    top, bottom, spread, top_win, observations = _period_top_bottom(
        frame,
        score_column,
    )

    correlation = (
        frame[score_column]
        .corr(frame["return_5d"], method="spearman")
        if observations
        else np.nan
    )

    return {
        "observations": observations,
        "top_return": top,
        "bottom_return": bottom,
        "spread": spread,
        "top_win_rate": top_win,
        "score_ic": float(correlation) if pd.notna(correlation) else np.nan,
    }


def _period_top_bottom(
    frame: pd.DataFrame,
    score_column: str,
) -> tuple[float, float, float, float, int]:
    daily_rows = []

    for _, group in frame.groupby("trade_date", sort=True):
        top, bottom, spread, top_win, observations = _daily_top_bottom(
            group,
            score_column,
        )

        if pd.isna(spread):
            continue

        daily_rows.append(
            {
                "top": top,
                "bottom": bottom,
                "spread": spread,
                "top_win": top_win,
                "observations": observations,
            }
        )

    if not daily_rows:
        return np.nan, np.nan, np.nan, np.nan, 0

    daily = pd.DataFrame(daily_rows)

    return (
        float(daily["top"].mean()),
        float(daily["bottom"].mean()),
        float(daily["spread"].mean()),
        float(daily["top_win"].mean()),
        int(daily["observations"].sum()),
    )


def _walk_forward_windows(
    dates: list[pd.Timestamp],
    train_days: int = TRAIN_DAYS,
    test_days: int = TEST_DAYS,
):
    start = 0
    window = 1

    while start + train_days + test_days <= len(dates):
        train_dates = dates[start : start + train_days]
        test_dates = dates[
            start + train_days : start + train_days + test_days
        ]

        yield window, train_dates, test_dates

        start += test_days
        window += 1


def run_walk_forward(
    df: pd.DataFrame,
    train_days: int = TRAIN_DAYS,
    test_days: int = TEST_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(df["trade_date"].dropna().unique().tolist())

    window_rows = []
    factor_rows = []

    for window, train_dates, test_dates in _walk_forward_windows(
        dates,
        train_days,
        test_days,
    ):
        train_start = train_dates[0]
        train_end = train_dates[-1]
        test_start = test_dates[0]
        test_end = test_dates[-1]

        train = df[df["trade_date"].isin(train_dates)].copy()
        test = df[df["trade_date"].isin(test_dates)].copy()

        directions, weights = _train_factor_model(train)

        print("\n" + "-" * 78)
        print(f"WINDOW {window}")
        print(f"Train : {train_start.date()} -> {train_end.date()}")
        print(f"Test  : {test_start.date()} -> {test_end.date()}")

        print("\nTRAIN FACTOR MODEL")
        for factor in FACTORS:
            print(
                f"{factor:<22} "
                f"weight={weights[factor]:.4f} "
                f"direction={'POSITIVE' if directions[factor] > 0 else 'NEGATIVE'}"
            )

        # Baseline and each candidate are fitted using TRAIN only.
        test_work = test.copy()

        baseline_test = _build_baseline_score(
            test_work,
            directions,
            weights,
        )
        test_work["baseline_score"] = baseline_test

        baseline_eval = _evaluate_period(
            test_work,
            "baseline_score",
        )

        candidate_results = {}

        for left, right in CANDIDATES:
            coefficient = _fit_interaction_coefficient(
                train,
                left,
                right,
            )

            candidate_name = f"{left} × {right}"

            test_work["candidate_score"] = _build_candidate_score_frozen(
                test_work,
                directions,
                weights,
                left,
                right,
                coefficient,
            )

            evaluation = _evaluate_period(
                test_work,
                "candidate_score",
            )

            candidate_results[candidate_name] = {
                "coefficient": coefficient,
                **evaluation,
            }

            factor_rows.append(
                {
                    "window": window,
                    "interaction": candidate_name,
                    "train_mean_ic": coefficient * 2.0,
                    "coefficient": coefficient,
                    "test_score_ic": evaluation["score_ic"],
                    "test_spread": evaluation["spread"],
                    "test_top_return": evaluation["top_return"],
                    "test_bottom_return": evaluation["bottom_return"],
                }
            )

        print("\nBASELINE OOS")
        print(
            f"Top return    : {baseline_eval['top_return']:+.4f}%"
        )
        print(
            f"Bottom return : {baseline_eval['bottom_return']:+.4f}%"
        )
        print(
            f"Spread        : {baseline_eval['spread']:+.4f}%"
        )

        for name, result in candidate_results.items():
            incremental = result["spread"] - baseline_eval["spread"]

            print(f"\n{name}")
            print(
                f"Coefficient   : {result['coefficient']:+.6f}"
            )
            print(
                f"Top return    : {result['top_return']:+.4f}%"
            )
            print(
                f"Bottom return : {result['bottom_return']:+.4f}%"
            )
            print(
                f"Spread        : {result['spread']:+.4f}%"
            )
            print(
                f"Incremental   : {incremental:+.4f}%"
            )

            window_rows.append(
                {
                    "window": window,
                    "train_start": train_start.date(),
                    "train_end": train_end.date(),
                    "test_start": test_start.date(),
                    "test_end": test_end.date(),
                    "interaction": name,
                    "baseline_spread": baseline_eval["spread"],
                    "candidate_spread": result["spread"],
                    "incremental_spread": incremental,
                    "baseline_top_return": baseline_eval["top_return"],
                    "candidate_top_return": result["top_return"],
                    "baseline_bottom_return": baseline_eval["bottom_return"],
                    "candidate_bottom_return": result["bottom_return"],
                    "candidate_score_ic": result["score_ic"],
                }
            )

    return pd.DataFrame(window_rows), pd.DataFrame(factor_rows)


def research_verdict(results: pd.DataFrame) -> dict:
    if results.empty:
        return {
            "decision": "FAIL",
            "reason": "No walk-forward results were produced.",
        }

    rows = []

    for interaction, group in results.groupby("interaction", sort=False):
        incremental = pd.to_numeric(
            group["incremental_spread"],
            errors="coerce",
        ).dropna()

        if incremental.empty:
            continue

        rows.append(
            {
                "interaction": interaction,
                "windows": int(len(incremental)),
                "average_incremental_spread": float(incremental.mean()),
                "median_incremental_spread": float(incremental.median()),
                "positive_windows": int((incremental > 0).sum()),
                "positive_window_pct": float((incremental > 0).mean() * 100),
                "worst_window": float(incremental.min()),
                "best_window": float(incremental.max()),
            }
        )

    summary = pd.DataFrame(rows)

    # Conservative research gate:
    # - at least 5 OOS windows
    # - positive incremental spread in >=60% of windows
    # - positive mean incremental spread
    # - positive median incremental spread
    summary["decision"] = np.where(
        (
            (summary["windows"] >= 5)
            & (summary["positive_window_pct"] >= 60.0)
            & (summary["average_incremental_spread"] > 0)
            & (summary["median_incremental_spread"] > 0)
        ),
        "PROMISING",
        "NOT_READY",
    )

    return {
        "summary": summary,
        "decision": (
            "PROMISING"
            if (summary["decision"] == "PROMISING").any()
            else "NOT_READY"
        ),
    }


def analyze(db_path: Path = DB_PATH) -> dict:
    print("\n" + "=" * 78)
    print("MARKETBOT C3.3 - INTERACTION CANDIDATE WALK-FORWARD")
    print("=" * 78)

    df = load_data(db_path)

    if df.empty:
        print("\nNo matched factor/outcome observations.")
        return {"decision": "FAIL", "observations": 0}

    print(f"\nObservations : {len(df):,}")
    print(f"Trading dates: {df['trade_date'].nunique():,}")
    print(f"Entities     : {df['entity'].nunique():,}")

    results, factor_results = run_walk_forward(df)

    print("\n" + "=" * 78)
    print("C3.3 OOS WINDOW RESULTS")
    print("=" * 78)

    if results.empty:
        print("No results.")
    else:
        print(results.round(4).to_string(index=False))

    print("\n" + "=" * 78)
    print("C3.3 AGGREGATE CANDIDATE RESULTS")
    print("=" * 78)

    verdict = research_verdict(results)
    summary = verdict["summary"]

    if summary.empty:
        print("No candidate summary available.")
    else:
        print(summary.round(4).to_string(index=False))

    print("\n" + "=" * 78)
    print("RESEARCH VERDICT")
    print("=" * 78)
    print(verdict["decision"])

    if verdict["decision"] == "PROMISING":
        print(
            "At least one C3.2 interaction shows positive and persistent "
            "incremental out-of-sample value."
        )
    else:
        print(
            "C3.2 interactions have NOT demonstrated sufficient incremental "
            "out-of-sample value."
        )

    print(
        "\nProduction scoring, production weights, challenger logic, "
        "and live trading were NOT changed."
    )

    return {
        "observations": len(df),
        "trading_dates": int(df["trade_date"].nunique()),
        "results": results,
        "factor_results": factor_results,
        "summary": summary,
        "decision": verdict["decision"],
    }


if __name__ == "__main__":
    analyze()
