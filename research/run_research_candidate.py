from __future__ import annotations

"""One-command Track C2 research runner.

Runs the candidate model, evaluates its walk-forward result, and records the
candidate in SQLite. It never modifies production scoring.
"""

import argparse
import json
from pathlib import Path

from research.regime_aware_model_v2 import DB_PATH, ModelConfig, load_data, run_walk_forward, summarize
from research.candidate_gate import evaluate
from database.research_candidate_registry import register


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and register a MarketBot research candidate")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output", type=Path, default=Path("research/artifacts"))
    parser.add_argument("--train-days", type=int, default=120)
    parser.add_argument("--test-days", type=int, default=20)
    args = parser.parse_args()

    cfg = ModelConfig(train_days=args.train_days, test_days=args.test_days)
    df = load_data(args.db)
    results, fits = run_walk_forward(df, cfg)
    summary = summarize(results)
    gate = evaluate(results)

    args.output.mkdir(parents=True, exist_ok=True)
    result_csv = args.output / "regime_aware_v2_walk_forward.csv"
    fits_csv = args.output / "regime_aware_v2_factor_fits.csv"
    gate_json = args.output / "regime_aware_v2_gate.json"
    results.to_csv(result_csv, index=False)
    fits.to_csv(fits_csv, index=False)
    gate_json.write_text(json.dumps(gate, indent=2), encoding="utf-8")

    register(args.db, "REGIME_AWARE_SHRINKAGE", "C2", gate, str(result_csv))

    print("\n" + "=" * 79)
    print("MARKETBOT RESEARCH CANDIDATE RUNNER")
    print("=" * 79)
    print(json.dumps({"summary": summary, "gate": gate}, indent=2))
    print("\nProduction scoring was not changed.")


if __name__ == "__main__":
    main()
