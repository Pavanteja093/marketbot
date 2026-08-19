"""
MarketBot V2 Probability Forecaster
-----------------------------------

Research-only multiclass probability forecasting for the existing V2 signal
ecosystem.

Contract:
    signal_history_v2 + forward_returns
        -> UP / FLAT / DOWN labels
        -> time-aware multiclass model
        -> probability calibration
        -> walk-forward validation
        -> research-only probability forecast

This module:
- DOES NOT modify production scoring.
- DOES NOT modify factor weights.
- DOES NOT modify trading logic.
- DOES NOT modify SQLite schema.
- DOES NOT write to SQLite.
- Treats V2 signals as the prediction population. It does not reconstruct
  signals that were not persisted in signal_history_v2.

The default target is the existing V2 5-trading-day forward return with a
configurable flat dead-band. The default FLAT threshold is deliberately
explicit and should be treated as a research parameter, not a production
truth.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "market_intelligence.db"

UP = "UP"
FLAT = "FLAT"
DOWN = "DOWN"
CLASSES = (DOWN, FLAT, UP)

# Explicit research defaults. These are NOT production trading thresholds.
DEFAULT_FLAT_THRESHOLD_PCT = 0.50
DEFAULT_HORIZON = "return_5d"
DEFAULT_MIN_TRAIN_DATES = 60
DEFAULT_TEST_DATES = 20
DEFAULT_STEP_DATES = 20
DEFAULT_MIN_CLASS_COUNT = 5

BASE_FEATURES = [
    "intelligence_score",
    "rank",
]

OPTIONAL_FACTOR_FEATURES = [
    "change_pct",
    "sector_strength",
    "position_pct",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

CATEGORICAL_FEATURES = ["sector"]


@dataclass(frozen=True)
class ForecastConfig:
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT
    horizon: str = DEFAULT_HORIZON
    min_train_dates: int = DEFAULT_MIN_TRAIN_DATES
    test_dates: int = DEFAULT_TEST_DATES
    step_dates: int = DEFAULT_STEP_DATES
    min_class_count: int = DEFAULT_MIN_CLASS_COUNT


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def _require_tables(conn: sqlite3.Connection, tables: Iterable[str]) -> None:
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    missing = sorted(set(tables) - existing)
    if missing:
        raise RuntimeError(
            "Probability forecaster requires missing tables: "
            + ", ".join(missing)
        )


def _resolve_symbol_column(columns: list[str]) -> str:
    for candidate in ("index_name", "symbol"):
        if candidate in columns:
            return candidate
    raise RuntimeError(
        "No symbol/index key found. Expected index_name or symbol."
    )


def load_dataset(
    db_path: Path = DEFAULT_DB_PATH,
    config: ForecastConfig | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Load persisted V2 signals and their realized forward returns.

    factor_history is optional. When available, its already-calculated
    features are joined at the same prediction date and symbol. No feature
    calculation or database write occurs here.
    """
    config = config or ForecastConfig()

    if config.horizon not in {"return_1d", "return_5d", "return_10d", "return_20d"}:
        raise ValueError(f"Unsupported horizon: {config.horizon}")

    conn = sqlite3.connect(db_path)
    try:
        _require_tables(conn, ("signal_history_v2", "forward_returns"))

        signal_cols = _table_columns(conn, "signal_history_v2")
        return_cols = _table_columns(conn, "forward_returns")

        required_signal = {"trade_date", "index_name", "sector", "intelligence_score", "rank"}
        missing_signal = sorted(required_signal - set(signal_cols))
        if missing_signal:
            raise RuntimeError(
                "signal_history_v2 missing required columns: "
                + ", ".join(missing_signal)
            )

        required_return = {"trade_date", "index_name", config.horizon}
        missing_return = sorted(required_return - set(return_cols))
        if missing_return:
            raise RuntimeError(
                "forward_returns missing required columns: "
                + ", ".join(missing_return)
            )

        query = f"""
            SELECT
                DATE(s.trade_date) AS trade_date,
                s.index_name,
                s.sector,
                s.intelligence_score,
                s.rank,
                f.{config.horizon} AS future_return
            FROM signal_history_v2 AS s
            INNER JOIN forward_returns AS f
                ON DATE(f.trade_date) = DATE(s.trade_date)
               AND f.index_name = s.index_name
            WHERE s.intelligence_score IS NOT NULL
              AND s.rank IS NOT NULL
              AND f.{config.horizon} IS NOT NULL
            ORDER BY DATE(s.trade_date), s.rank
        """

        df = pd.read_sql_query(query, conn)

        if df.empty:
            return df, list(BASE_FEATURES)

        # Optional enrichment from factor_history. This is read-only and
        # defensive because historical schema variants use index_name/symbol.
        if "factor_history" in {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            factor_cols = _table_columns(conn, "factor_history")
            factor_key = _resolve_symbol_column(factor_cols)
            usable = [
                c for c in OPTIONAL_FACTOR_FEATURES
                if c in factor_cols and c not in df.columns
            ]

            if usable:
                select_cols = ", ".join(
                    ["DATE(trade_date) AS trade_date", f"{factor_key} AS index_name"]
                    + usable
                )
                factor_df = pd.read_sql_query(
                    f"""
                        SELECT {select_cols}
                        FROM factor_history
                        WHERE trade_date IS NOT NULL
                    """,
                    conn,
                )
                if not factor_df.empty:
                    factor_df["trade_date"] = pd.to_datetime(
                        factor_df["trade_date"], errors="coerce"
                    ).dt.date
                    df["trade_date"] = pd.to_datetime(
                        df["trade_date"], errors="coerce"
                    ).dt.date
                    factor_df = factor_df.drop_duplicates(
                        subset=["trade_date", "index_name"],
                        keep="last",
                    )
                    df = df.merge(
                        factor_df,
                        on=["trade_date", "index_name"],
                        how="left",
                    )

        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
        df["future_return"] = pd.to_numeric(
            df["future_return"], errors="coerce"
        )
        df = df.dropna(
            subset=["trade_date", "future_return", "intelligence_score", "rank"]
        ).copy()

        df["label"] = classify_return(
            df["future_return"],
            flat_threshold_pct=config.flat_threshold_pct,
        )

        feature_columns = [
            c for c in BASE_FEATURES + OPTIONAL_FACTOR_FEATURES
            if c in df.columns
        ]

        return df.sort_values(["trade_date", "rank"]).reset_index(drop=True), feature_columns
    finally:
        conn.close()


def classify_return(
    returns: pd.Series,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> pd.Series:
    """Convert realized forward returns into UP / FLAT / DOWN."""
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


def _make_estimator(
    numeric_features: list[str],
    categorical_features: list[str],
) -> Pipeline:
    transformers = [
        (
            "numeric",
            Pipeline(
                [
                    ("imputer", _SimpleMedianImputer()),
                    ("scale", StandardScaler()),
                ]
            ),
            numeric_features,
        ),
    ]

    if categorical_features:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", _SimpleMostFrequentImputer()),
                        (
                            "onehot",
                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=False,
                            ),
                        ),
                    ]
                ),
                categorical_features,
            )
        )

    from sklearn.compose import ColumnTransformer

    preprocess = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    model = LogisticRegression(
        max_iter=3000,
        class_weight=None,
        random_state=42,
    )

    return Pipeline(
        [
            ("preprocess", preprocess),
            ("model", model),
        ]
    )


class _SimpleMedianImputer(BaseEstimator, TransformerMixin):
    """Tiny dataframe-compatible transformer; keeps this module self-contained."""

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.columns_ = list(X.columns)
        self.medians_ = X.median(numeric_only=True)
        return self

    def transform(self, X):
        X = pd.DataFrame(X).copy()
        for col in self.columns_:
            X[col] = pd.to_numeric(X[col], errors="coerce")
            X[col] = X[col].fillna(self.medians_.get(col, 0.0))
        return X

    def get_feature_names_out(self, input_features=None):
        return np.asarray(
            input_features if input_features is not None else self.columns_,
            dtype=object,
        )


class _SimpleMostFrequentImputer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.columns_ = list(X.columns)
        self.modes_ = {}
        for col in self.columns_:
            mode = X[col].dropna().mode()
            self.modes_[col] = mode.iloc[0] if not mode.empty else "UNKNOWN"
        return self

    def transform(self, X):
        X = pd.DataFrame(X).copy()
        for col in self.columns_:
            X[col] = X[col].fillna(self.modes_.get(col, "UNKNOWN")).astype(str)
        return X

    def get_feature_names_out(self, input_features=None):
        return np.asarray(
            input_features if input_features is not None else self.columns_,
            dtype=object,
        )




def _has_all_classes(y: pd.Series) -> bool:
    return set(y.dropna().unique()) == set(CLASSES)


class TemperatureScaledClassifier:
    """Multiclass temperature scaling using a strictly later calibration slice."""

    def __init__(self, estimator, temperature: float = 1.0):
        self.estimator = estimator
        self.temperature = float(temperature)
        self.classes_ = None

    def fit(self, X_fit, y_fit, X_cal, y_cal):
        self.estimator.fit(X_fit, y_fit)
        self.classes_ = np.asarray(self.estimator.classes_)

        if not _has_all_classes(pd.Series(y_cal)):
            self.temperature = 1.0
            return self

        base_proba = np.clip(
            self.estimator.predict_proba(X_cal),
            1e-12,
            1.0,
        )
        y_idx = pd.Series(y_cal).map(
            {c: i for i, c in enumerate(self.classes_)}
        ).to_numpy()

        best_temperature = 1.0
        best_loss = float("inf")

        # Deterministic research calibration grid. Temperature > 1 softens
        # probabilities; temperature < 1 sharpens them.
        for temperature in np.linspace(0.50, 3.00, 101):
            scaled = self._scale(base_proba, temperature)
            loss = -np.mean(np.log(scaled[np.arange(len(y_idx)), y_idx]))
            if loss < best_loss:
                best_loss = loss
                best_temperature = float(temperature)

        self.temperature = best_temperature
        return self

    @staticmethod
    def _scale(probabilities: np.ndarray, temperature: float) -> np.ndarray:
        logits = np.log(np.clip(probabilities, 1e-12, 1.0))
        logits = logits / float(temperature)
        logits = logits - logits.max(axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        return exp_logits / exp_logits.sum(axis=1, keepdims=True)

    def predict_proba(self, X):
        base = np.clip(
            self.estimator.predict_proba(X),
            1e-12,
            1.0,
        )
        return self._scale(base, self.temperature)

    def predict(self, X):
        probabilities = self.predict_proba(X)
        return self.classes_[np.argmax(probabilities, axis=1)]


def fit_calibrated_model(
    train: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[object, str]:
    """
    Fit the base multiclass model on the earlier part of the training period
    and temperature-calibrate it on a strictly later calibration slice.

    This prevents random CV from mixing future observations into calibration.
    """
    numeric = [
        c for c in feature_columns
        if c not in CATEGORICAL_FEATURES
    ]
    categorical = [
        c for c in CATEGORICAL_FEATURES
        if c in feature_columns
    ]

    if not _has_all_classes(train["label"]):
        raise ValueError("Training data does not contain UP, FLAT and DOWN.")

    ordered = train.sort_values("trade_date").reset_index(drop=True)
    dates = sorted(ordered["trade_date"].dt.normalize().unique())

    # Reserve the last ~20% of training dates for calibration.
    if len(dates) < 10:
        estimator = _make_estimator(numeric, categorical)
        estimator.fit(train[feature_columns], train["label"])
        return estimator, "uncalibrated_logistic_regression"

    calibration_date_count = max(5, int(round(len(dates) * 0.20)))
    calibration_dates = set(dates[-calibration_date_count:])
    fit_dates = set(dates[:-calibration_date_count])

    fit_part = ordered[
        ordered["trade_date"].dt.normalize().isin(fit_dates)
    ].copy()
    calibration_part = ordered[
        ordered["trade_date"].dt.normalize().isin(calibration_dates)
    ].copy()

    if (
        fit_part.empty
        or calibration_part.empty
        or not _has_all_classes(fit_part["label"])
        or not _has_all_classes(calibration_part["label"])
    ):
        estimator = _make_estimator(numeric, categorical)
        estimator.fit(train[feature_columns], train["label"])
        return estimator, "uncalibrated_logistic_regression"

    estimator = _make_estimator(numeric, categorical)
    calibrated = TemperatureScaledClassifier(estimator)

    calibrated.fit(
        fit_part[feature_columns],
        fit_part["label"],
        calibration_part[feature_columns],
        calibration_part["label"],
    )
    return calibrated, "time_holdout_temperature_scaled"

def _class_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["label"].value_counts()
    return {c: int(counts.get(c, 0)) for c in CLASSES}


def walk_forward(
    df: pd.DataFrame,
    feature_columns: list[str],
    config: ForecastConfig,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Expanding-window walk-forward evaluation.

    Each test block occurs strictly after its training block. Calibration,
    when available, is itself time-aware within the training block.
    """
    if df.empty:
        return pd.DataFrame(), []

    dates = sorted(df["trade_date"].dt.normalize().unique())
    folds = []
    predictions = []

    start = config.min_train_dates
    while start < len(dates):
        test_end = min(start + config.test_dates, len(dates))
        test_dates = dates[start:test_end]

        train_dates = dates[:start]
        train = df[df["trade_date"].dt.normalize().isin(train_dates)].copy()
        test = df[df["trade_date"].dt.normalize().isin(test_dates)].copy()

        if test.empty:
            break

        train_counts = _class_counts(train)
        if (
            len(train_dates) < config.min_train_dates
            or min(train_counts.values()) < config.min_class_count
        ):
            folds.append(
                {
                    "train_start": str(train_dates[0].date()),
                    "train_end": str(train_dates[-1].date()),
                    "test_start": str(test_dates[0].date()),
                    "test_end": str(test_dates[-1].date()),
                    "status": "SKIPPED_INSUFFICIENT_CLASS_HISTORY",
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "train_down": train_counts[DOWN],
                    "train_flat": train_counts[FLAT],
                    "train_up": train_counts[UP],
                }
            )
            start += config.step_dates
            continue

        try:
            model, calibration_status = fit_calibrated_model(
                train, feature_columns
            )
            probabilities = model.predict_proba(test[feature_columns])
            model_classes = list(model.classes_)
        except Exception as exc:
            folds.append(
                {
                    "train_start": str(train_dates[0].date()),
                    "train_end": str(train_dates[-1].date()),
                    "test_start": str(test_dates[0].date()),
                    "test_end": str(test_dates[-1].date()),
                    "status": "SKIPPED_MODEL_ERROR",
                    "error": str(exc),
                    "train_rows": len(train),
                    "test_rows": len(test),
                }
            )
            start += config.step_dates
            continue

        proba_frame = pd.DataFrame(
            probabilities,
            columns=model_classes,
            index=test.index,
        ).reindex(columns=CLASSES, fill_value=0.0)

        predicted = proba_frame.idxmax(axis=1)

        for idx in test.index:
            row = test.loc[idx]
            predictions.append(
                {
                    "trade_date": row["trade_date"].date().isoformat(),
                    "index_name": row["index_name"],
                    "sector": row.get("sector"),
                    "rank": (int(row["rank"]) if pd.notna(row.get("rank")) else None),
                    "intelligence_score": float(row["intelligence_score"]),
                    "future_return": float(row["future_return"]),
                    "actual": row["label"],
                    "p_down": float(proba_frame.loc[idx, DOWN]),
                    "p_flat": float(proba_frame.loc[idx, FLAT]),
                    "p_up": float(proba_frame.loc[idx, UP]),
                    "predicted": predicted.loc[idx],
                    "calibration_status": calibration_status,
                    "fold_train_end": train_dates[-1].date().isoformat(),
                }
            )

        folds.append(
            {
                "train_start": str(train_dates[0].date()),
                "train_end": str(train_dates[-1].date()),
                "test_start": str(test_dates[0].date()),
                "test_end": str(test_dates[-1].date()),
                "status": "SUCCESS",
                "calibration": calibration_status,
                "train_rows": len(train),
                "test_rows": len(test),
                "train_down": train_counts[DOWN],
                "train_flat": train_counts[FLAT],
                "train_up": train_counts[UP],
            }
        )

        start += config.step_dates

    return pd.DataFrame(predictions), folds


def _binary_ece(
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Expected calibration error for one one-vs-rest class."""
    probabilities = np.asarray(probabilities, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)

    if len(probabilities) == 0:
        return float("nan")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (
            (probabilities >= left)
            & (
                probabilities < right
                if right < 1.0
                else probabilities <= right
            )
        )
        if not np.any(mask):
            continue
        weight = np.mean(mask)
        confidence = np.mean(probabilities[mask])
        observed = np.mean(outcomes[mask])
        ece += weight * abs(confidence - observed)
    return float(ece)


def multiclass_ece(
    probabilities: np.ndarray,
    actual: pd.Series,
    classes: tuple[str, ...] = CLASSES,
    n_bins: int = 10,
) -> float:
    """Mean one-vs-rest ECE across UP/FLAT/DOWN."""
    actual_values = actual.to_numpy()
    errors = []
    for class_index, class_name in enumerate(classes):
        outcomes = (actual_values == class_name).astype(float)
        errors.append(
            _binary_ece(
                probabilities[:, class_index],
                outcomes,
                n_bins=n_bins,
            )
        )
    return float(np.mean(errors))


def evaluate_probabilities(
    predictions: pd.DataFrame,
) -> dict[str, float | int | None]:
    """Return proper scoring rules and classification metrics."""
    if predictions.empty:
        return {
            "n": 0,
            "accuracy": None,
            "balanced_accuracy": None,
            "log_loss": None,
            "brier_multiclass": None,
            "multiclass_ece": None,
        }

    y = predictions["actual"]
    proba = predictions[["p_down", "p_flat", "p_up"]].to_numpy()
    classes = list(CLASSES)
    actual_idx = y.map({c: i for i, c in enumerate(classes)}).to_numpy()

    return {
        "n": int(len(predictions)),
        "accuracy": float(accuracy_score(y, predictions["predicted"])),
        "balanced_accuracy": float(
            balanced_accuracy_score(y, predictions["predicted"])
        ),
        "log_loss": float(
            log_loss(y, proba, labels=classes)
        ),
        "brier_multiclass": float(
            np.mean(
                np.sum(
                    (proba - np.eye(len(classes))[actual_idx]) ** 2,
                    axis=1,
                )
            )
        ),
        "multiclass_ece": multiclass_ece(
            proba,
            y,
            classes=CLASSES,
        ),
    }


def fit_current_forecast(
    df: pd.DataFrame,
    feature_columns: list[str],
    config: ForecastConfig,
) -> dict:
    """
    Fit on all currently available completed V2 observations and forecast the
    latest persisted V2 signal date.

    This is research output only. It does not persist the forecast.
    """
    if df.empty:
        raise ValueError("No completed V2 observations available.")

    latest_date = df["trade_date"].max()
    latest = df[df["trade_date"] == latest_date].copy()

    if latest.empty:
        raise ValueError("No latest V2 observations available.")

    counts = _class_counts(df)
    if min(counts.values()) < config.min_class_count:
        raise ValueError(
            "Insufficient class history for a three-class forecast: "
            f"{counts}"
        )

    model, calibration_status = fit_calibrated_model(df, feature_columns)
    probabilities = model.predict_proba(latest[feature_columns])
    model_classes = list(model.classes_)

    proba = (
        pd.DataFrame(probabilities, columns=model_classes, index=latest.index)
        .reindex(columns=CLASSES, fill_value=0.0)
    )

    result = latest[
        ["trade_date", "index_name", "sector", "rank", "intelligence_score"]
    ].copy()

    result["p_down"] = proba[DOWN]
    result["p_flat"] = proba[FLAT]
    result["p_up"] = proba[UP]
    result["forecast"] = proba.idxmax(axis=1)
    result["calibration_status"] = calibration_status

    return {
        "forecast_date": latest_date.date().isoformat(),
        "rows": result.sort_values("rank").reset_index(drop=True),
        "model": model,
        "calibration_status": calibration_status,
        "class_counts": counts,
    }


def run_research(
    db_path: Path = DEFAULT_DB_PATH,
    config: ForecastConfig | None = None,
    output_path: Path | None = None,
) -> dict:
    config = config or ForecastConfig()

    print("\n" + "=" * 78)
    print("MARKETBOT V2 PROBABILITY FORECASTER â€” RESEARCH ONLY")
    print("=" * 78)

    df, feature_columns = load_dataset(db_path, config)

    print(f"Completed V2 observations : {len(df):,}")
    print(f"Feature columns            : {', '.join(feature_columns)}")
    print(f"Target horizon             : {config.horizon}")
    print(f"FLAT threshold             : Â±{config.flat_threshold_pct:.2f}%")

    if df.empty:
        print("\nINSUFFICIENT DATA")
        print("No persisted V2 signals have completed outcomes yet.")
        return {
            "dataset": df,
            "feature_columns": feature_columns,
            "predictions": pd.DataFrame(),
            "folds": [],
            "metrics": evaluate_probabilities(pd.DataFrame()),
            "forecast": None,
        }

    counts = _class_counts(df)
    print(
        "Class counts                : "
        f"DOWN={counts[DOWN]:,}, FLAT={counts[FLAT]:,}, UP={counts[UP]:,}"
    )

    predictions, folds = walk_forward(df, feature_columns, config)
    metrics = evaluate_probabilities(predictions)

    print("\n" + "-" * 78)
    print("WALK-FORWARD VALIDATION")
    print("-" * 78)
    for fold in folds:
        print(
            f"{fold['train_start']} -> {fold['train_end']} | "
            f"test {fold['test_start']} -> {fold['test_end']} | "
            f"{fold['status']}"
        )

    print("\n" + "-" * 78)
    print("PROBABILITY METRICS")
    print("-" * 78)
    for key, value in metrics.items():
        if value is None:
            print(f"{key:<24}: N/A")
        elif isinstance(value, float):
            print(f"{key:<24}: {value:.6f}")
        else:
            print(f"{key:<24}: {value}")

    forecast = None
    latest_counts_ok = min(counts.values()) >= config.min_class_count
    if latest_counts_ok:
        try:
            forecast = fit_current_forecast(
                df, feature_columns, config
            )
            print("\n" + "-" * 78)
            print("CURRENT RESEARCH FORECAST")
            print("-" * 78)
            print(
                f"Forecast date              : {forecast['forecast_date']}"
            )
            print(
                f"Calibration                : {forecast['calibration_status']}"
            )
            print(
                forecast["rows"][
                    [
                        "rank",
                        "index_name",
                        "forecast",
                        "p_up",
                        "p_flat",
                        "p_down",
                        "intelligence_score",
                    ]
                ].to_string(index=False)
            )
        except ValueError as exc:
            print(f"\nCurrent forecast unavailable: {exc}")
    else:
        print(
            "\nCURRENT FORECAST: withheld until every class has at least "
            f"{config.min_class_count} completed observations."
        )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        predictions.to_csv(output_path, index=False)
        print(f"\nWalk-forward predictions written: {output_path}")

    print("\nSTATUS: SUCCESS")
    return {
        "dataset": df,
        "feature_columns": feature_columns,
        "predictions": predictions,
        "folds": folds,
        "metrics": metrics,
        "forecast": forecast,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Research-only MarketBot V2 probability forecaster."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to market_intelligence.db",
    )
    parser.add_argument(
        "--flat-threshold",
        type=float,
        default=DEFAULT_FLAT_THRESHOLD_PCT,
        help="Absolute forward-return percentage treated as FLAT.",
    )
    parser.add_argument(
        "--min-train-dates",
        type=int,
        default=DEFAULT_MIN_TRAIN_DATES,
    )
    parser.add_argument(
        "--test-dates",
        type=int,
        default=DEFAULT_TEST_DATES,
    )
    parser.add_argument(
        "--step-dates",
        type=int,
        default=DEFAULT_STEP_DATES,
    )
    parser.add_argument(
        "--min-class-count",
        type=int,
        default=DEFAULT_MIN_CLASS_COUNT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional CSV for OOS research predictions.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = ForecastConfig(
        flat_threshold_pct=args.flat_threshold,
        min_train_dates=args.min_train_dates,
        test_dates=args.test_dates,
        step_dates=args.step_dates,
        min_class_count=args.min_class_count,
    )
    run_research(
        db_path=args.db,
        config=config,
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

