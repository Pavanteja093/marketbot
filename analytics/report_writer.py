from pathlib import Path

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def save_report(report_name, text):

    path = REPORT_DIR / report_name

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Report saved: {path}")