from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def export_report(text):

    report_folder = BASE_DIR / "reports"

    report_folder.mkdir(exist_ok=True)

    report = report_folder / "daily_report.txt"

    with open(report, "w", encoding="utf-8") as f:

        f.write(text)

    print(f"Report saved -> {report}")