from __future__ import annotations

"""Build deterministic Scenario × Weapon research batches.

This module is a planning layer only.

It:
- reads the stable research queue CSV
- groups relationships into deterministic research batches
- writes a new batch artifact

It does NOT:
- access SQLite
- execute research
- execute candidate modules
- modify production systems
- modify existing research artifacts
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_ARTIFACT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_research_queue.csv"
)

OUTPUT_ARTIFACT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_research_batches.csv"
)


REQUIRED_COLUMNS = {
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
}


OUTPUT_COLUMNS = [
    "batch_id",
    "batch_priority",
    "queue_priority",
    "research_priority",
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "scenario_observations",
    "oos_windows",
    "target_oos_windows",
    "oos_gap_to_target",
    "eligibility_status",
    "queue_action",
    "batch_action",
    "batch_reason",
    "batch_rank",
]


QUEUE_PRIORITY_ORDER = {
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
            "Research queue artifact is missing required columns: "
            + ", ".join(missing)
        )


def load_queue(
    path: Path = INPUT_ARTIFACT,
) -> pd.DataFrame:
    """Read the stable queue artifact."""
    return pd.read_csv(path)


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    validate_input(frame)

    work = frame.copy(deep=True)

    work["queue_priority"] = (
        work["queue_priority"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    work["research_priority"] = (
        work["research_priority"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    work["queue_action"] = (
        work["queue_action"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    work["scenario_observations"] = pd.to_numeric(
        work["scenario_observations"],
        errors="coerce",
    )

    work["oos_windows"] = pd.to_numeric(
        work["oos_windows"],
        errors="coerce",
    )

    work["target_oos_windows"] = pd.to_numeric(
        work["target_oos_windows"],
        errors="coerce",
    )

    work["oos_gap_to_target"] = pd.to_numeric(
        work["oos_gap_to_target"],
        errors="coerce",
    )

    numeric_columns = [
        "scenario_observations",
        "oos_windows",
        "target_oos_windows",
        "oos_gap_to_target",
    ]

    for column in numeric_columns:
        if work[column].isna().any():
            raise ValueError(
                f"{column} contains non-numeric or missing values."
            )

        work[column] = work[column].astype(int)

    return work


def _batch_action(queue_priority: str) -> str:
    if queue_priority == "P0":
        return "CONTINUE_OOS_BATCH"

    if queue_priority in {"P1", "P2"}:
        return "START_OOS_BATCH"

    return "WAIT_FOR_SCENARIO_HISTORY"


def _batch_reason(
    queue_priority: str,
    scenario_id: str,
    relationship_count: int,
) -> str:

    if queue_priority == "P0":
        return (
            f"{scenario_id} has existing OOS evidence; "
            f"group {relationship_count} continuation relationship(s) "
            "to efficiently reach the current OOS milestone."
        )

    if queue_priority == "P1":
        return (
            f"{scenario_id} is a mature research scenario with no "
            f"existing OOS evidence for {relationship_count} relationship(s)."
        )

    if queue_priority == "P2":
        return (
            f"{scenario_id} has researchable but less-mature scenario "
            f"coverage across {relationship_count} relationship(s)."
        )

    return (
        f"{scenario_id} does not currently have sufficient scenario "
        "history for immediate OOS research."
    )


def build_batches(
    queue: pd.DataFrame,
) -> pd.DataFrame:
    """Convert the stable queue into deterministic research batches."""

    work = _normalise(queue)

    if work.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # One batch per:
    #   queue priority
    #   research priority
    #   scenario
    #
    # This keeps candidates for the same scenario together while keeping
    # P0/P1/P2/P3 workloads strictly separated.
    group_columns = [
        "queue_priority",
        "research_priority",
        "scenario_id",
        "primary_scenario",
        "fingerprint",
        "queue_action",
    ]

    grouped = work.groupby(
        group_columns,
        sort=False,
        dropna=False,
    )

    batch_rows = []

    batch_definitions = []

    for group_key, group in grouped:
        (
            queue_priority,
            research_priority,
            scenario_id,
            primary_scenario,
            fingerprint,
            queue_action,
        ) = group_key

        batch_definitions.append(
            {
                "queue_priority": str(queue_priority),
                "research_priority": str(research_priority),
                "scenario_id": str(scenario_id),
                "primary_scenario": str(primary_scenario),
                "fingerprint": str(fingerprint),
                "queue_action": str(queue_action),
                "group": group.copy(deep=True),
            }
        )

    batch_definitions.sort(
        key=lambda item: (
            QUEUE_PRIORITY_ORDER.get(
                item["queue_priority"],
                99,
            ),
            RESEARCH_PRIORITY_ORDER.get(
                item["research_priority"],
                99,
            ),
            item["scenario_id"],
            item["primary_scenario"],
            item["fingerprint"],
        )
    )

    for batch_rank, definition in enumerate(
        batch_definitions,
        start=1,
    ):

        group = definition["group"]

        queue_priority = definition["queue_priority"]
        research_priority = definition["research_priority"]
        scenario_id = definition["scenario_id"]
        primary_scenario = definition["primary_scenario"]
        fingerprint = definition["fingerprint"]
        queue_action = definition["queue_action"]

        batch_id = f"BATCH_{batch_rank:03d}"

        batch_action = _batch_action(queue_priority)

        batch_reason = _batch_reason(
            queue_priority=queue_priority,
            scenario_id=scenario_id,
            relationship_count=len(group),
        )

        # Candidates within a batch are always deterministic.
        group = group.sort_values(
            [
                "candidate",
                "oos_windows",
                "scenario_observations",
            ],
            ascending=[
                True,
                False,
                False,
            ],
            kind="mergesort",
        )

        for _, source in group.iterrows():

            batch_rows.append(
                {
                    "batch_id": batch_id,
                    "batch_priority": queue_priority,
                    "queue_priority": queue_priority,
                    "research_priority": research_priority,
                    "scenario_id": source["scenario_id"],
                    "primary_scenario": source["primary_scenario"],
                    "fingerprint": source["fingerprint"],
                    "candidate": source["candidate"],
                    "scenario_observations": int(
                        source["scenario_observations"]
                    ),
                    "oos_windows": int(
                        source["oos_windows"]
                    ),
                    "target_oos_windows": int(
                        source["target_oos_windows"]
                    ),
                    "oos_gap_to_target": int(
                        source["oos_gap_to_target"]
                    ),
                    "eligibility_status": source[
                        "eligibility_status"
                    ],
                    "queue_action": queue_action,
                    "batch_action": batch_action,
                    "batch_reason": batch_reason,
                    "batch_rank": batch_rank,
                }
            )

    return pd.DataFrame(
        batch_rows,
        columns=OUTPUT_COLUMNS,
    )


def write_batches(
    batches: pd.DataFrame,
    path: Path = OUTPUT_ARTIFACT,
) -> None:
    """Write only the new batch artifact."""
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    batches.to_csv(
        path,
        index=False,
    )


def build_from_artifact(
    input_path: Path = INPUT_ARTIFACT,
    output_path: Path = OUTPUT_ARTIFACT,
) -> pd.DataFrame:

    queue = load_queue(input_path)

    batches = build_batches(queue)

    write_batches(
        batches,
        output_path,
    )

    return batches


def _print_report(
    batches: pd.DataFrame,
) -> None:

    print("\n" + "=" * 80)
    print(
        "MARKETBOT - SCENARIO WEAPON RESEARCH BATCH PLAN"
    )
    print("=" * 80)

    total_relationships = len(batches)

    if batches.empty:
        print("\nTotal relationships : 0")
        print("Total batches       : 0")
        print("P0 batches          : 0")
        print("P1 batches          : 0")
        print("P2 batches          : 0")
        print("P3 waiting batches  : 0")
        print("Executable relations: 0")
        print("Waiting relations   : 0")
        print("Remaining OOS gap   : 0")
        print("\nTop batch: NONE")

        print(
            f"\nSaved: {OUTPUT_ARTIFACT}"
        )

        print(
            "READ-ONLY: no SQLite or production systems were modified."
        )

        return

    batch_table = (
        batches[
            [
                "batch_id",
                "batch_priority",
                "research_priority",
                "scenario_id",
                "candidate",
            ]
        ]
        .drop_duplicates(
            subset=["batch_id"]
        )
    )

    p0_batches = int(
        (batch_table["batch_priority"] == "P0").sum()
    )

    p1_batches = int(
        (batch_table["batch_priority"] == "P1").sum()
    )

    p2_batches = int(
        (batch_table["batch_priority"] == "P2").sum()
    )

    p3_batches = int(
        (batch_table["batch_priority"] == "P3").sum()
    )

    executable_mask = batches[
        "batch_priority"
    ].isin(["P0", "P1", "P2"])

    executable_relationships = int(
        executable_mask.sum()
    )

    waiting_relationships = int(
        (~executable_mask).sum()
    )

    total_oos_gap = int(
        batches["oos_gap_to_target"].sum()
    )

    print(
        f"\nTotal relationships : {total_relationships:,}"
    )

    print(
        f"Total batches       : {len(batch_table):,}"
    )

    print(
        f"P0 batches          : {p0_batches:,}"
    )

    print(
        f"P1 batches          : {p1_batches:,}"
    )

    print(
        f"P2 batches          : {p2_batches:,}"
    )

    print(
        f"P3 waiting batches  : {p3_batches:,}"
    )

    print(
        f"Executable relations: {executable_relationships:,}"
    )

    print(
        f"Waiting relations   : {waiting_relationships:,}"
    )

    print(
        f"Remaining OOS gap   : {total_oos_gap:,} windows"
    )

    first_batch = batch_table.iloc[0]

    first_rows = batches[
        batches["batch_id"]
        == first_batch["batch_id"]
    ]

    print("\nTOP BATCH")

    print(
        f"Batch ID            : {first_batch['batch_id']}"
    )

    print(
        f"Scenario            : {first_batch['scenario_id']}"
    )

    print(
        f"Priority            : {first_batch['batch_priority']}"
    )

    print(
        f"Research priority   : {first_batch['research_priority']}"
    )

    print(
        f"Action              : "
        f"{first_rows.iloc[0]['batch_action']}"
    )

    print(
        f"Relationships       : {len(first_rows)}"
    )

    print("\nTOP 10 BATCHES")

    display = batch_table.head(10)

    print(
        display.to_string(
            index=False
        )
    )

    print(
        f"\nSaved: {OUTPUT_ARTIFACT}"
    )

    print(
        "READ-ONLY: no SQLite or production systems were modified."
    )


def main() -> None:
    batches = build_from_artifact()

    _print_report(
        batches
    )


if __name__ == "__main__":
    main()