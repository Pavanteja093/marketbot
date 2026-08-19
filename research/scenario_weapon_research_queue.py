from __future__ import annotations

"""Build a deterministic, read-only Scenario × Weapon research workload."""

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_ARTIFACT = BASE_DIR / "research" / "artifacts" / "scenario_weapon_eligibility.csv"
OUTPUT_ARTIFACT = BASE_DIR / "research" / "artifacts" / "scenario_weapon_research_queue.csv"

TARGET_OOS_WINDOWS = 10

REQUIRED_COLUMNS = {
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "scenario_observations",
    "oos_windows",
    "eligibility_status",
    "research_priority",
}

OUTPUT_COLUMNS = [
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "scenario_observations",
    "oos_windows",
    "target_oos_windows",
    "oos_gap_to_target",
    "eligibility_status",
    "research_priority",
    "queue_priority",
    "queue_action",
    "queue_reason",
]

PRIORITY_ORDER = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
}

RESEARCH_PRIORITY_ORDER = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(
            "Scenario Weapon eligibility artifact is missing required columns: "
            + ", ".join(missing)
        )


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    validate_input(frame)

    work = frame.copy(deep=True)

    work["scenario_observations"] = pd.to_numeric(
        work["scenario_observations"], errors="coerce"
    )
    work["oos_windows"] = pd.to_numeric(work["oos_windows"], errors="coerce")

    if work["scenario_observations"].isna().any():
        raise ValueError("scenario_observations contains non-numeric values.")
    if work["oos_windows"].isna().any():
        raise ValueError("oos_windows contains non-numeric values.")

    work["scenario_observations"] = work["scenario_observations"].astype(int)
    work["oos_windows"] = work["oos_windows"].astype(int)

    if (work["scenario_observations"] < 0).any():
        raise ValueError("scenario_observations cannot be negative.")
    if (work["oos_windows"] < 0).any():
        raise ValueError("oos_windows cannot be negative.")

    work["eligibility_status"] = (
        work["eligibility_status"].fillna("").astype(str).str.strip()
    )
    work["research_priority"] = (
        work["research_priority"].fillna("").astype(str).str.strip().str.upper()
    )

    return work


def classify_queue(row: pd.Series) -> tuple[str, str, str]:
    """Return queue_priority, action, reason without changing the source row."""

    observations = int(row["scenario_observations"])
    oos_windows = int(row["oos_windows"])
    eligibility = str(row["eligibility_status"]).upper()
    research_priority = str(row["research_priority"]).upper()

    if eligibility == "INSUFFICIENT_SCENARIO_HISTORY":
        return (
            "P3",
            "WAIT_FOR_SCENARIO_HISTORY",
            "Scenario history is insufficient for immediate OOS research.",
        )

    if oos_windows > 0 and oos_windows < TARGET_OOS_WINDOWS:
        gap = TARGET_OOS_WINDOWS - oos_windows
        return (
            "P0",
            "CONTINUE_OOS",
            f"Existing genuine OOS evidence exists; continue until the "
            f"{TARGET_OOS_WINDOWS}-window milestone ({gap} windows remaining).",
        )

    if (
        oos_windows == 0
        and eligibility == "RESEARCHABLE_NO_EVIDENCE"
    ):
        if research_priority == "HIGH":
            return (
                "P1",
                "START_OOS_RESEARCH",
                "Researchable relationship with mature/high-priority scenario history and no OOS evidence.",
            )

        return (
            "P2",
            "START_OOS_RESEARCH",
            "Researchable relationship with less-mature scenario history; start after mature P1 workload.",
        )

    if (
        oos_windows == 0
        and observations > 0
        and eligibility not in {"INSUFFICIENT_SCENARIO_HISTORY"}
    ):
        if research_priority == "HIGH":
            return (
                "P1",
                "START_OOS_RESEARCH",
                "Scenario history exists and the relationship has no OOS evidence; high research priority.",
            )
        return (
            "P2",
            "START_OOS_RESEARCH",
            "Scenario history exists but the relationship is lower research priority.",
        )

    # Relationships already at or beyond the first milestone have no
    # immediate P0 continuation gap. Keep them in the deterministic queue
    # without claiming that a new OOS study is required.
    if oos_windows >= TARGET_OOS_WINDOWS:
        return (
            "P2",
            "MILESTONE_REACHED",
            f"The first {TARGET_OOS_WINDOWS}-window OOS milestone is already reached; "
            "no immediate continuation gap remains.",
        )

    return (
        "P3",
        "WAIT_FOR_SCENARIO_HISTORY",
        "No actionable OOS workload can be scheduled from the eligibility artifact.",
    )


def build_queue(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert eligibility rows into an ordered research workload."""

    work = _normalise(frame)

    rows = []
    for _, source in work.iterrows():
        queue_priority, action, reason = classify_queue(source)

        oos_windows = int(source["oos_windows"])
        gap = max(TARGET_OOS_WINDOWS - oos_windows, 0)

        rows.append(
            {
                "scenario_id": source["scenario_id"],
                "primary_scenario": source["primary_scenario"],
                "fingerprint": source["fingerprint"],
                "candidate": source["candidate"],
                "scenario_observations": int(source["scenario_observations"]),
                "oos_windows": oos_windows,
                "target_oos_windows": TARGET_OOS_WINDOWS,
                "oos_gap_to_target": gap,
                "eligibility_status": source["eligibility_status"],
                "research_priority": source["research_priority"],
                "queue_priority": queue_priority,
                "queue_action": action,
                "queue_reason": reason,
            }
        )

    result = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    if result.empty:
        return result

    result["_queue_rank"] = result["queue_priority"].map(PRIORITY_ORDER)
    result["_research_rank"] = result["research_priority"].map(
        RESEARCH_PRIORITY_ORDER
    ).fillna(99)

    # Required deterministic ranking:
    # 1 queue_priority
    # 2 research_priority
    # 3 current oos_windows
    # 4 scenario_observations
    # 5 scenario_id
    # 6 candidate
    result = (
        result.sort_values(
            [
                "_queue_rank",
                "_research_rank",
                "oos_windows",
                "scenario_observations",
                "scenario_id",
                "candidate",
            ],
            ascending=[True, True, False, False, True, True],
            kind="mergesort",
        )
        .drop(columns=["_queue_rank", "_research_rank"])
        .reset_index(drop=True)
    )

    return result[OUTPUT_COLUMNS]


def load_eligibility(path: Path = INPUT_ARTIFACT) -> pd.DataFrame:
    """Load the stable eligibility artifact without touching SQLite."""
    return pd.read_csv(path)


def write_queue(queue: pd.DataFrame, path: Path = OUTPUT_ARTIFACT) -> None:
    """Write only the new queue artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(path, index=False)


def build_from_artifact(
    input_path: Path = INPUT_ARTIFACT,
    output_path: Path = OUTPUT_ARTIFACT,
) -> pd.DataFrame:
    source = load_eligibility(input_path)
    queue = build_queue(source)
    write_queue(queue, output_path)
    return queue


def _print_report(queue: pd.DataFrame) -> None:
    print("\n" + "=" * 92)
    print("MARKETBOT - SCENARIO WEAPON RESEARCH QUEUE")
    print("=" * 92)

    print(f"\nTotal relationships : {len(queue):,}")

    counts = queue["queue_priority"].value_counts() if not queue.empty else {}
    print(f"P0 count            : {counts.get('P0', 0):,}")
    print(f"P1 count            : {counts.get('P1', 0):,}")
    print(f"P2 count            : {counts.get('P2', 0):,}")
    print(f"P3 count            : {counts.get('P3', 0):,}")

    remaining = int(queue["oos_gap_to_target"].sum()) if not queue.empty else 0
    print(f"Total OOS gap       : {remaining:,} windows")

    if queue.empty:
        print("\nTop research queue  : EMPTY")
    else:
        print("\nTOP RESEARCH QUEUE")
        display = queue[
            [
                "queue_priority",
                "research_priority",
                "scenario_id",
                "candidate",
                "scenario_observations",
                "oos_windows",
                "oos_gap_to_target",
                "queue_action",
            ]
        ].head(15)
        print(display.to_string(index=False))

    print(f"\nSaved: {OUTPUT_ARTIFACT}")
    print("READ-ONLY: no SQLite or production systems were modified.")


def main() -> None:
    queue = build_from_artifact()
    _print_report(queue)


if __name__ == "__main__":
    main()
