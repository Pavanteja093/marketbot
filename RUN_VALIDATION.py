"""
MARKETBOT â€” COMPACT VALIDATION RUNNER

Run from the MarketBot root:
    python .\RUN_VALIDATION.py

The runner executes each validation command, captures full output internally,
and prints only:
  - PASS/FAIL
  - a compact final status
  - error/traceback lines when a command fails

Full logs are saved to validation_logs\ for later inspection.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "validation_logs"
LOG_DIR.mkdir(exist_ok=True)

COMMANDS = [
    ("PCR CONTRACT", ["python", "-m", "tests.test_pcr_engine_contract"]),
    ("MAX PAIN CONTRACT", ["python", "-m", "tests.test_max_pain_engine_contract"]),
    ("OI REGRESSION CONTRACT", ["python", "-m", "tests.test_oi_engine_contract"]),
    ("OPTION INTELLIGENCE SEMANTIC TEST",
     ["python", "option_intelligence_test.py"]),
]

def error_lines(text: str) -> list[str]:
    lines = text.splitlines()
    patterns = (
        "Traceback",
        "Error:",
        "ERROR",
        "FAILED",
        "FAIL:",
        "ModuleNotFoundError",
        "ImportError",
        "SyntaxError",
        "DatabaseError",
        "OperationalError",
        "FileNotFoundError",
        "PermissionError",
    )
    found = []
    capture = False

    for line in lines:
        if any(p in line for p in patterns):
            capture = True
        if capture:
            found.append(line)
            if len(found) >= 20:
                break

    return found

def run(name: str, command: list[str]) -> bool:
    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")
    print(f"COMMAND: {' '.join(command)}")

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    log_path = LOG_DIR / f"{stamp}_{safe_name}.log"
    log_path.write_text(result.stdout, encoding="utf-8", errors="replace")

    if result.returncode == 0:
        print("STATUS : PASS")
        return True

    print(f"STATUS : FAIL (exit code {result.returncode})")
    print("ERROR DETAILS:")
    details = error_lines(result.stdout)
    if details:
        print("\n".join(details))
    else:
        print(result.stdout[-3000:])

    print(f"FULL LOG: {log_path}")
    return False

def main() -> int:
    print("=" * 70)
    print("MARKETBOT â€” COMPACT MULTI-TRACK VALIDATION")
    print("=" * 70)
    print(f"ROOT: {ROOT}")

    passed = 0
    failed = 0

    for name, command in COMMANDS:
        if run(name, command):
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 70)
    print("FINAL VALIDATION REPORT")
    print("=" * 70)
    print(f"PASS : {passed}")
    print(f"FAIL : {failed}")

    if failed:
        print("STATUS : FAIL")
        print("ACTION : Review ONLY the failed track error details above.")
        return 1

    print("STATUS : PASS")
    print("ACTION : All configured validation tracks completed successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

