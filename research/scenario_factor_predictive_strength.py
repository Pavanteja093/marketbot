from __future__ import annotations

"""MarketBot - Scenario x Factor Predictive Strength.

Research-only layer. Compares existing scenario x factor-state evidence with
scenario and global 5-day return baselines. SQLite is opened read-only.
"""
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE_DIR / "research" / "artifacts"
DEFAULT_INPUT = ARTIFACT_DIR / "scenario_factor_conditional_evidence.csv"
DEFAULT_OUTPUT = ARTIFACT_DIR / "scenario_factor_predictive_strength.csv"
DB_PATH = BASE_DIR / "market_intelligence.db"

REQUIRED_COLUMNS = [
    "primary_scenario", "factor", "factor_state", "observations",
    "scenario_dates", "symbols", "positive_5d_pct", "mean_return_5d",
    "median_return_5d", "worst_return_5d", "best_return_5d",
]

OUTPUT_COLUMNS = REQUIRED_COLUMNS + [
    "scenario_baseline_observations", "scenario_baseline_positive_5d_pct",
    "scenario_baseline_mean_return_5d", "global_baseline_observations",
    "global_baseline_positive_5d_pct", "global_baseline_mean_return_5d",
    "positive_rate_lift_vs_scenario", "mean_return_lift_vs_scenario",
    "positive_rate_lift_vs_global", "mean_return_lift_vs_global",
    "predictive_strength_status", "predictive_strength_reason",
]


def _validate_evidence(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Conditional evidence input is missing required columns: " + ", ".join(missing))


def _baseline_stats(db_path: Path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        scenario_sql = """
        SELECT s.primary_scenario, COUNT(*) AS observations,
               AVG(fr.return_5d) AS mean_return_5d,
               AVG(CASE WHEN fr.return_5d > 0 THEN 1.0 ELSE 0.0 END) * 100.0 AS positive_5d_pct
        FROM factor_history f
        INNER JOIN market_scenario_history s ON DATE(f.trade_date)=DATE(s.trade_date)
        INNER JOIN forward_returns fr ON DATE(fr.trade_date)=DATE(f.trade_date)
            AND fr.index_name=f.index_name
        WHERE fr.return_5d IS NOT NULL
        GROUP BY s.primary_scenario
        ORDER BY s.primary_scenario
        """
        global_sql = """
        SELECT COUNT(*), AVG(return_5d),
               AVG(CASE WHEN return_5d > 0 THEN 1.0 ELSE 0.0 END) * 100.0
        FROM forward_returns WHERE return_5d IS NOT NULL
        """
        scenarios = pd.read_sql_query(scenario_sql, conn)
        r = conn.execute(global_sql).fetchone()
        return scenarios, {
            "observations": int(r[0] or 0),
            "mean_return_5d": float(r[1]) if r[1] is not None else None,
            "positive_5d_pct": float(r[2]) if r[2] is not None else None,
        }
    finally:
        conn.close()


def _classify(row):
    obs = int(row["observations"])
    mean_lift = row["mean_return_lift_vs_scenario"]
    pct_lift = row["positive_rate_lift_vs_scenario"]
    if obs < 30:
        return "INSUFFICIENT", "Conditional relationship has fewer than 30 observations."
    if pd.isna(mean_lift) or pd.isna(pct_lift):
        return "UNAVAILABLE", "Scenario baseline is unavailable."
    if obs >= 100 and mean_lift >= 0.50 and pct_lift >= 5.0:
        return "STRONG_POSITIVE", "Large sample with positive return and hit-rate lift."
    if obs >= 50 and mean_lift >= 0.20 and pct_lift >= 2.0:
        return "POSITIVE", "Meaningful positive lift versus the scenario baseline."
    if obs >= 50 and mean_lift <= -0.20 and pct_lift <= -2.0:
        return "NEGATIVE", "Meaningful negative lift versus the scenario baseline."
    return "WEAK_OR_MIXED", "Evidence does not show a stable directional lift."


def assess_predictive_strength(evidence, scenario_baselines, global_baseline):
    _validate_evidence(evidence)
    work = evidence.copy(deep=True)
    for c in REQUIRED_COLUMNS[3:]:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    baseline = scenario_baselines.copy()
    baseline["primary_scenario"] = baseline["primary_scenario"].astype(str)
    work = work.merge(
        baseline[["primary_scenario", "observations", "mean_return_5d", "positive_5d_pct"]].rename(
            columns={"observations":"scenario_baseline_observations",
                     "mean_return_5d":"scenario_baseline_mean_return_5d",
                     "positive_5d_pct":"scenario_baseline_positive_5d_pct"}),
        on="primary_scenario", how="left", validate="many_to_one")
    work["global_baseline_observations"] = global_baseline["observations"]
    work["global_baseline_positive_5d_pct"] = global_baseline["positive_5d_pct"]
    work["global_baseline_mean_return_5d"] = global_baseline["mean_return_5d"]
    work["positive_rate_lift_vs_scenario"] = work["positive_5d_pct"] - work["scenario_baseline_positive_5d_pct"]
    work["mean_return_lift_vs_scenario"] = work["mean_return_5d"] - work["scenario_baseline_mean_return_5d"]
    work["positive_rate_lift_vs_global"] = work["positive_5d_pct"] - work["global_baseline_positive_5d_pct"]
    work["mean_return_lift_vs_global"] = work["mean_return_5d"] - work["global_baseline_mean_return_5d"]
    statuses = work.apply(_classify, axis=1, result_type="expand")
    work["predictive_strength_status"] = statuses[0]
    work["predictive_strength_reason"] = statuses[1]
    return work[OUTPUT_COLUMNS].sort_values(
        ["predictive_strength_status", "mean_return_lift_vs_scenario", "positive_rate_lift_vs_scenario",
         "primary_scenario", "factor", "factor_state"],
        ascending=[True, False, False, True, True, True], kind="mergesort").reset_index(drop=True)


def run(input_path=DEFAULT_INPUT, output_path=DEFAULT_OUTPUT, db_path=DB_PATH):
    evidence = pd.read_csv(input_path)
    baselines, global_baseline = _baseline_stats(Path(db_path))
    result = assess_predictive_strength(evidence, baselines, global_baseline)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, lineterminator="\n")
    return result


def main():
    result = run()
    print("=" * 80)
    print("MARKETBOT - SCENARIO × FACTOR PREDICTIVE STRENGTH")
    print("=" * 80)
    print(f"Relationships assessed : {len(result)}")
    counts = result["predictive_strength_status"].value_counts()
    for s in ["STRONG_POSITIVE","POSITIVE","WEAK_OR_MIXED","NEGATIVE","INSUFFICIENT","UNAVAILABLE"]:
        print(f"{s:<20}: {int(counts.get(s, 0))}")
    print("\nTOP PREDICTIVE LIFTS")
    cols=["primary_scenario","factor","factor_state","observations","positive_5d_pct",
          "scenario_baseline_positive_5d_pct","positive_rate_lift_vs_scenario",
          "mean_return_lift_vs_scenario","predictive_strength_status"]
    print(result.sort_values(["mean_return_lift_vs_scenario","positive_rate_lift_vs_scenario"],
                             ascending=[False,False],kind="mergesort")[cols].head(15).to_string(index=False))
    print(f"\nSaved: {DEFAULT_OUTPUT}")
    print("READ-ONLY: SQLite opened read-only; no production or trading changes.")

if __name__ == "__main__":
    main()
