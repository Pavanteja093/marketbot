from pathlib import Path

from research import scenario_weapon_execution_readiness as _impl

TRACK_B = _impl.TRACK_B
TRACK_C = _impl.TRACK_C
REQUIRED_QUEUE = _impl.REQUIRED_QUEUE
OUTPUT_COLUMNS = _impl.OUTPUT_COLUMNS

_load_scenario_history = _impl._load_scenario_history
_candidate_dates = _impl._candidate_dates


def audit(queue, db_path: Path = _impl.DEFAULT_DB):
    original_history = _impl._load_scenario_history
    original_dates = _impl._candidate_dates

    _impl._load_scenario_history = _load_scenario_history
    _impl._candidate_dates = _candidate_dates

    try:
        return _impl.audit(queue, db_path)
    finally:
        _impl._load_scenario_history = original_history
        _impl._candidate_dates = original_dates


def run(db_path: Path = _impl.DEFAULT_DB,
        queue_path: Path = _impl.DEFAULT_QUEUE):
    return _impl.run(db_path, queue_path)


__all__ = [
    "TRACK_B",
    "TRACK_C",
    "REQUIRED_QUEUE",
    "OUTPUT_COLUMNS",
    "_load_scenario_history",
    "_candidate_dates",
    "audit",
    "run",
]
