import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.upstox_config import ACCESS_TOKEN

print("TYPE   :", type(ACCESS_TOKEN))
print("LENGTH :", len(ACCESS_TOKEN))
print("START  :", ACCESS_TOKEN[:10])
print("END    :", ACCESS_TOKEN[-10:])