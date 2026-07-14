import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import upstox_client

from config.upstox_config import ACCESS_TOKEN

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

options_api = upstox_client.OptionsApi(client)

print(dir(options_api))