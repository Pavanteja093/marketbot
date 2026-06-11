import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

print("\n" + "=" * 70)
print("MARKETBOT DAILY UPDATE")
print("=" * 70)

tasks = [

    (
        "Stocks Collector",
        BASE_DIR / "data_collectors" / "stocks.py"
    ),

    (
        "Indices Collector",
        BASE_DIR / "data_collectors" / "indices.py"
    ),

    (
        "FII DII Collector",
        BASE_DIR / "data_collectors" / "fii_dii.py"
    ),

    (
        "Stock Scoring",
        BASE_DIR / "analytics" / "stock_scoring.py"
    ),

    (
        "Master Morning Report",
        BASE_DIR / "reports" / "master_morning_report.py"
    )
]

for task_name, script_path in tasks:

    print(f"\nRunning: {task_name}")

    try:

        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            print("SUCCESS")

        else:
 
            print("FAILED")
            print(result.stderr)

    except Exception as e:

        print("ERROR")
        print(e)

print("\n" + "=" * 70)
print("DAILY UPDATE COMPLETED")
print("=" * 70)