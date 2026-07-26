"""
Global Project Settings
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = PROJECT_ROOT / "market_intelligence.db"

LOG_FOLDER = PROJECT_ROOT / "logs"

BACKUP_FOLDER = PROJECT_ROOT / "backups"

REPORT_FOLDER = PROJECT_ROOT / "reports"

TIMEZONE = "Asia/Kolkata"

BROKER = "UPSTOX"