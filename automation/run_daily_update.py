import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def run_module(
    name,
    module,
    required=True
):

    print("\n" + "-" * 70)
    print(name)
    print("-" * 70)

    try:

        result = subprocess.run(
            [
                PYTHON,
                "-m",
                module
            ],
            cwd=BASE_DIR,
            text=True,
            capture_output=True
        )

        if result.stdout:
            print(result.stdout)

        if result.returncode != 0:

            print(
                f"FAILED: {module}"
            )

            if result.stderr:
                print(result.stderr)

            if required:
                return False

            return True

        print(
            f"SUCCESS: {module}"
        )

        return True

    except Exception as exc:

        print(
            f"ERROR running {module}: "
            f"{exc}"
        )

        return not required


def main():

    print("\n" + "=" * 75)
    print("MARKETBOT PRODUCTION DAILY UPDATE")
    print("=" * 75)

    failures = []

    # ========================================================
    # 1. DATABASE SYNCHRONIZATION
    # ========================================================

    synchronization = [

        (
            "Market Data Repair",
            "automation.repair_market_data"
        ),

        (
            "Database Doctor",
            "automation.database_doctor"
        ),

    ]

    for name, module in synchronization:

        if not run_module(
            name,
            module,
            required=True
        ):

            failures.append(module)

            print(
                "\nCRITICAL: "
                "Database synchronization failed."
            )

            return False

    # ========================================================
    # 2. DATA COLLECTION
    # ========================================================

    collectors = [

        (
            "Stocks Collector",
            "data_collectors.stocks"
        ),

        (
            "Indices Collector",
            "data_collectors.indices"
        ),

        (
            "Option Chain Collector",
            "data_collectors.option_chain_upstox"
        ),

        (
            "FII DII Collector",
            "data_collectors.fii_dii"
        ),

    ]

    for name, module in collectors:

        if not run_module(
            name,
            module,
            required=True
        ):

            failures.append(module)

    if failures:

        print(
            "\nDATA COLLECTION FAILED."
        )

        return False

    # ========================================================
    # 3. FEATURE / FACTOR PIPELINE
    # ========================================================

    analytics = [

        (
            "Feature Builder",
            "analytics.feature_builder"
        ),

        (
            "Factor Builder",
            "analytics.factor_builder"
        ),

        (
            "Historical Factor Builder",
            "analytics.factor_history_builder"
        ),

        (
            "Ranking Engine",
            "analytics.ranking_engine"
        ),

    ]

    for name, module in analytics:

        if not run_module(
            name,
            module,
            required=True
        ):

            failures.append(module)

    # ========================================================
    # 4. MARKET INTELLIGENCE
    # ========================================================

    intelligence = [

        (
            "Stock Scoring V1",
            "analytics.stock_scoring"
        ),

        (
            "Stock Scoring V2",
            "analytics.stock_scoring_v2"
        ),

        (
            "Prediction Engine",
            "analytics.prediction_engine_v2"
        ),

        (
            "Signal Generator",
            "analytics.signal_generator"
        ),

        (
            "Trade Quality",
            "analytics.trade_quality"
        ),

    ]

    for name, module in intelligence:

        if not run_module(
            name,
            module,
            required=False
        ):

            failures.append(module)

    # ========================================================
    # 5. HISTORY
    # ========================================================

    history = [

        (
            "Prediction History",
            "research.prediction_history"
        ),

        (
            "Forward Returns",
            "research.forward_returns"
        ),

    ]

    for name, module in history:

        if not run_module(
            name,
            module,
            required=False
        ):

            failures.append(module)

    # ========================================================
    # 6. RESEARCH
    # ========================================================

    research = [

        (
            "Factor Research",
            "research.factor_research"
        ),

        (
            "Walk Forward Validation",
            "research.walk_forward"
        ),

        (
            "Factor Performance",
            "research.factor_performance"
        ),

    ]

    for name, module in research:

        if not run_module(
            name,
            module,
            required=False
        ):

            failures.append(module)

    # ========================================================
    # 7. LEARNING
    # ========================================================

    learning = [

        (
            "Learning Engine",
            "learning.learning_engine"
        ),

        (
            "Weight Research",
            "learning.weight_optimizer"
        ),

    ]

    for name, module in learning:

        if not run_module(
            name,
            module,
            required=False
        ):

            failures.append(module)

    # ========================================================
    # 8. FINAL HEALTH CHECK
    # ========================================================

    health = [

        (
            "Database Doctor",
            "automation.database_doctor"
        ),

        (
            "Database Self-Repair Check",
            "automation.self_repair"
        ),

    ]

    for name, module in health:

        if not run_module(
            name,
            module,
            required=True
        ):

            failures.append(module)

    # ========================================================
    # FINAL STATUS
    # ========================================================

    print("\n" + "=" * 75)
    print("MARKETBOT DAILY UPDATE RESULT")
    print("=" * 75)

    if failures:

        print(
            "\nSTATUS: COMPLETED WITH FAILURES"
        )

        print("\nFailed modules:")

        for module in failures:

            print(
                f"  - {module}"
            )

        return False

    print(
        "\nSTATUS: SUCCESS"
    )

    print(
        "All required pipeline stages completed."
    )

    return True


if __name__ == "__main__":

    success = main()

    sys.exit(
        0 if success else 1
    )