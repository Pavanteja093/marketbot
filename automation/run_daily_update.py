import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

print("\n" + "=" * 70)
print("MARKETBOT DAILY UPDATE")
print("=" * 70)

DATA_COLLECTION = [
        (
            "Stocks Collector",
            BASE_DIR / "data_collectors" / "stocks.py"
        ),

        (
            "Indices Collector",
            BASE_DIR / "data_collectors" / "indices.py"
        ),

        (
            "Option Chain Collector",
            BASE_DIR / "data_collectors" / "option_chain_upstox.py"
        ),

        (
            "FII DII Collector",
            BASE_DIR / "data_collectors" / "fii_dii.py"
        )
]

FEATURE_ENGINEERING = [

    (
        "Feature Builder",
        BASE_DIR / "analytics" / "feature_builder.py"
    ),

    (
        "Sector Strength",
        BASE_DIR / "analytics" / "sector_strength.py"
    ),

    (
        "Market Brain",
        BASE_DIR / "analytics" / "market_brain.py"
    )
]
    
MARKET_INTELLIGENCE = [

    (
        "Stock Scoring V1",
        BASE_DIR / "analytics" / "stock_scoring.py"
    ),

    (
        "Stock Scoring V2",
        BASE_DIR / "analytics" / "stock_scoring_v2.py"
    )
]

HISTORY = [

    (
        "Save Factor History",
        BASE_DIR / "analytics" / "save_factor_history.py"
    ),

    (
        "Prediction History",
        BASE_DIR / "research" / "prediction_history.py"
    ),

    (
        "Market Prediction History",
        BASE_DIR / "analytics" / "market_prediction_history.py"
    ),

    (
        "Signal History V2",
        BASE_DIR / "analytics" / "signal_history_v2.py"
    )
]

LEARNING = [

    (
        "Outcome Tracker",
        BASE_DIR / "learning" / "outcome_tracker.py"
    ),

]

PHASES = [

    ("DATA COLLECTION", DATA_COLLECTION),

    ("FEATURE ENGINEERING", FEATURE_ENGINEERING),

    ("MARKET INTELLIGENCE", MARKET_INTELLIGENCE),

    ("HISTORY", HISTORY),

    ("LEARNING", LEARNING)

]
    
for phase_name, phase_tasks in PHASES:

        print("\n" + "=" * 70)
        print(phase_name)
        print("=" * 70)

        for task_name, script_path in phase_tasks:

            try:

                relative_script = script_path.relative_to(BASE_DIR)

                module_name = (
                    str(relative_script)
                    .replace("\\", ".")
                    .replace("/", ".")
                    .replace(".py", "")
                )

                result = subprocess.run(
                    ["python", "-m", module_name],
                    capture_output=True,
                    text=True,
                    cwd=BASE_DIR
                )

                if result.returncode == 0:

                    print("SUCCESS")

                    if result.stdout:
                        print(result.stdout)
                    
                else:

                    print("FAILED")

                    if result.stderr:
                        print(result.stderr)

            except Exception as e:

                print("ERROR")
                print(e)

print("\n" + "=" * 70)
print("DAILY UPDATE COMPLETED")
print("=" * 70)