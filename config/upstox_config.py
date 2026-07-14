from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
API_KEY = os.getenv("UPSTOX_API_KEY")
API_SECRET = os.getenv("UPSTOX_API_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")