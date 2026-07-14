from pathlib import Path
import sys
from datetime import datetime

# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(
    str(BASE_DIR / "analytics")
)

# --------------------------------------------------
# IMPORTS
# --------------------------------------------------

from global_markets import get_global_markets
from india_economy import get_india_economy
from analytics.market_brain import get_market_brain
from trading_playbook import get_trading_playbook
from stock_reason_engine import get_stock_reasons

# --------------------------------------------------
# REPORT GENERATOR
# --------------------------------------------------

def generate_report():

    markets = get_global_markets()

    economy = get_india_economy()

    brain = get_market_brain()

    playbook = get_trading_playbook()

    stock_reasons = get_stock_reasons()

    report_lines = []

    report_lines.append("=" * 70)
    report_lines.append("MASTER MORNING REPORT")
    report_lines.append("=" * 70)

    # --------------------------------------------------
    # GLOBAL MARKETS
    # --------------------------------------------------

    report_lines.append("")
    report_lines.append("GLOBAL MARKETS")
    report_lines.append("-" * 40)

    report_lines.append(
        markets.to_string(index=False)
    )

    # --------------------------------------------------
    # INDIA ECONOMY
    # --------------------------------------------------

    report_lines.append("")
    report_lines.append("INDIA ECONOMY")
    report_lines.append("-" * 40)

    report_lines.append(
        f"Inflation : {economy['inflation_view']}"
    )

    report_lines.append(
        f"Rates     : {economy['rate_view']}"
    )

    # --------------------------------------------------
    # MARKET BRAIN
    # --------------------------------------------------

    report_lines.append("")
    report_lines.append("MARKET BRAIN")
    report_lines.append("-" * 40)

    report_lines.append(
        f"View       : {brain['market_view']}"
    )

    report_lines.append(
        f"Regime     : {brain['market_regime']}"
    )

    report_lines.append(
        f"Sector     : {brain['leading_sector']}"
    )

    report_lines.append(
        f"FII Flow   : {brain['fii_flow']}"
    )

    report_lines.append(
        f"Risk Score : {brain['risk_score']}/100"
    )

    # --------------------------------------------------
    # TRADING PLAYBOOK
    # --------------------------------------------------

    report_lines.append("")
    report_lines.append("TRADING PLAYBOOK")
    report_lines.append("-" * 40)

    report_lines.append(
        f"Index View   : {playbook['index_view']}"
    )

    report_lines.append(
        f"Options View : {playbook['options_view']}"
    )

    report_lines.append(
        f"Best Sector  : {playbook['strongest_sector']}"
    )

    report_lines.append(
        f"Confidence   : {playbook['confidence_score']}/100"
    )

    # --------------------------------------------------
    # TOP STOCKS WITH REASONS
    # --------------------------------------------------

    report_lines.append("")
    report_lines.append("TOP STOCKS WITH REASONS")
    report_lines.append("-" * 40)

    for stock in stock_reasons[:5]:

        report_lines.append("")

        report_lines.append(
            stock["symbol"]
        )

        report_lines.append(
            f"Sector : {stock['sector']}"
        )

        report_lines.append(
            f"Score  : {stock['score']}"
        )

        report_lines.append(
            f"Reason : {stock['reason']}"
        )

    # --------------------------------------------------
    # ACTION
    # --------------------------------------------------

    report_lines.append("")
    report_lines.append("ACTION")
    report_lines.append("-" * 40)

    report_lines.append(
        brain["action"]
    )

    report_text = "\n".join(
        report_lines
    )

    # --------------------------------------------------
    # PRINT REPORT
    # --------------------------------------------------

    print("\n")
    print(report_text)

    # --------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------

    history_dir = (
        BASE_DIR /
        "reports" /
        "history"
    )

    history_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = datetime.now().strftime(
        "%Y-%m-%d"
    ) + ".txt"

    report_file = (
        history_dir /
        filename
    )

    with open(
        report_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report_text)

    print("\n")
    print("=" * 70)
    print(
        f"Report Saved : {report_file}"
    )
    print("=" * 70)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    generate_report()