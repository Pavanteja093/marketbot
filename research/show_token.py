# research/show_token.py

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.upstox_config import ACCESS_TOKEN

print(type(ACCESS_TOKEN))
print(len(ACCESS_TOKEN))
print(ACCESS_TOKEN[:30])